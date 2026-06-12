# tests/bug_23025_harness.py — 검증된 bash 하니스 래퍼
# 원칙 1: 오탐 잡아가며 다듬은 판정 로직은 재작성하지 않는다. 호출하고 결과만 수용.
# 원칙 2: 총 실행 수와 PASS 수의 source of truth 는 하니스 summary.txt 실집계다.
#         실행되지 않은 회차를 PASS 로 합성하지 않는다. summary 부재/모순 = INFRA_FAILURE (PASS 0건).
# 원칙 3: results.csv 는 WARN/FAIL 상세(사유·아티팩트) 근거로만 사용한다.
import csv
import os
import shutil
import subprocess

from tests.base_test import BaseTest, InfraFailure

HARNESS = os.path.join(os.path.dirname(__file__), "..", "harness",
                       "bug23025_close_all_verify.sh")


class SummaryParseError(Exception):
    """summary.txt 파싱 실패 또는 내부 모순."""


# wrapper 가 관리하는 하니스 옵션 — extra_args 로 재지정(우회) 금지
RESERVED_HARNESS_OPTS = {"-s", "--serial", "-S", "--scenarios", "-n", "--count",
                         "-o", "--out", "--menu", "--no-menu"}


def _under_system_root(path):
    sysroot = os.path.normpath(os.environ.get("SystemRoot", r"C:\Windows")).lower()
    return os.path.normpath(path).lower().startswith(sysroot)


def _is_git_path(path):
    """경로 구성요소 정확 일치 기준 Git Bash 판정 — `git` 또는 `portablegit*` 만 인정.

    부분문자열 검사 금지: notgit / GitHub / git-tools / cygwin / msys 거부.
    """
    for comp in os.path.normpath(path).lower().split(os.sep):
        if comp == "git" or comp.startswith("portablegit"):
            return True
    return False


def resolve_bash(configured=None):
    """bash 실행 경로 안전 resolve — Git Bash 만 허용.

    bare "bash" 의존 금지: WSL/System32 bash 는 MSYS 경로 변환·시맨틱이 달라
    하니스 오동작 위험 → InfraFailure. config.local.yaml 의 bash_path 명시가 우선.
    """
    if configured:
        if not os.path.isfile(configured):
            raise InfraFailure(f"bash_path 미존재: {configured}")
        if _under_system_root(configured):
            raise InfraFailure(
                f"bash_path 가 WSL/System32 bash: {configured} — Git Bash 경로를 지정하세요")
        if not _is_git_path(configured):
            raise InfraFailure(
                f"bash_path 가 Git Bash 경로가 아님: {configured} (cygwin/msys 등 거부)")
        return configured

    candidates = [
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                     "Git", "bin", "bash.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     "Git", "bin", "bash.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Git", "bin", "bash.exe"),
    ]
    for cand in candidates:
        if cand and os.path.isfile(cand):
            return cand

    found = shutil.which("bash")
    if found and not _under_system_root(found) and _is_git_path(found):
        return found
    raise InfraFailure(
        f"Git Bash 미발견 (PATH bash={found or '없음'}) — config.local.yaml 에 bash_path 지정")


def parse_harness_summary(path):
    """하니스 print_summary tee 산출물 파싱.

    반환: (rows, total)
      rows  = [{"name", "count", "pass", "warn", "fail"}, ...]  (시나리오별)
      total = {"count", "pass", "warn", "fail"}                 (합계 행)
    내부 모순(행 내 합 불일치 / 시나리오 합 vs 합계 불일치) 시 SummaryParseError.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\n") for ln in f]

    sep_idx = [i for i, ln in enumerate(lines) if ln.strip().startswith("-----")]
    if len(sep_idx) < 2:
        raise SummaryParseError(f"요약 표 구분선을 찾지 못함: {path}")

    rows = []
    for ln in lines[sep_idx[0] + 1:sep_idx[1]]:
        tokens = ln.split()
        if len(tokens) < 5:
            raise SummaryParseError(f"시나리오 행 형식 오류: {ln!r}")
        try:
            c, p, w, fl = (int(t) for t in tokens[-4:])
        except ValueError:
            raise SummaryParseError(f"시나리오 행 숫자 파싱 실패: {ln!r}")
        name = " ".join(tokens[:-4])
        if c != p + w + fl:
            raise SummaryParseError(
                f"[{name}] count({c}) != pass+warn+fail({p}+{w}+{fl})")
        rows.append({"name": name, "count": c, "pass": p, "warn": w, "fail": fl})

    total = None
    for ln in lines[sep_idx[1] + 1:]:
        tokens = ln.split()
        if tokens and tokens[0] == "합계":
            if len(tokens) < 5:
                raise SummaryParseError(f"합계 행 형식 오류: {ln!r}")
            try:
                c, p, w, fl = (int(t) for t in tokens[1:5])
            except ValueError:
                raise SummaryParseError(f"합계 행 숫자 파싱 실패: {ln!r}")
            total = {"count": c, "pass": p, "warn": w, "fail": fl}
            break
    if total is None:
        raise SummaryParseError(f"합계 행을 찾지 못함: {path}")

    if total["count"] != total["pass"] + total["warn"] + total["fail"]:
        raise SummaryParseError(
            f"합계 행 내부 모순: count({total['count']}) != "
            f"{total['pass']}+{total['warn']}+{total['fail']}")
    for key in ("count", "pass", "warn", "fail"):
        row_sum = sum(r[key] for r in rows)
        if row_sum != total[key]:
            raise SummaryParseError(
                f"시나리오 합({key}={row_sum}) != 합계 행({key}={total[key]})")
    return rows, total


class Bug23025Harness(BaseTest):
    """BUG-23025: Simple mode 모두닫기 → blank home. ../analysis/bugs/BUG-23025.md 참조."""

    def __init__(self, config):
        super().__init__(config)
        c = config.get("bug_23025", {})
        self.scenarios = c.get("scenarios", "basic,hwkeys,toggle,reentry,screenoff")
        self.count = int(c.get("count", self.repeat))
        self.extra_args = c.get("extra_args", [])  # 예: ["--hwkeys", "..."]
        self.bash_path_cfg = config.get("bash_path", "")  # 미지정 시 Git Bash 자동 resolve

    def _infra(self, reason, artifact=None):
        self.results.append(("INFRA_FAILURE", reason, artifact))
        print(f"  [INFRA_FAILURE] {reason}")
        return self.results

    @staticmethod
    def _latest_run_dir(out_root):
        if not os.path.isdir(out_root):
            return None
        run_dirs = sorted(d for d in os.listdir(out_root)
                          if os.path.isdir(os.path.join(out_root, d)))
        return os.path.join(out_root, run_dirs[-1]) if run_dirs else None

    REQUIRED_CSV_FIELDS = ("scenario", "index", "level", "reason", "artifact_dir")

    @classmethod
    def _read_detail_rows(cls, csv_path):
        """results.csv 의 WARN/FAIL 상세 행 (구조화).

        파일 부재 / 헤더 누락 / 미등록 level / index 비정수 = ValueError (호출부에서 INFRA).
        하니스는 시작 시 헤더를 반드시 생성하므로 파일 부재 = 비정상 실행.
        WARN/FAIL 외 level 을 조용히 건너뛰면 PASS 복원으로 위장될 수 있다.
        """
        details = []
        if not os.path.isfile(csv_path):
            raise ValueError("results.csv 부재 — 하니스 비정상 실행 의심 (헤더는 시작 시 생성됨)")
        with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            fields = set(reader.fieldnames or [])
            missing = [c for c in cls.REQUIRED_CSV_FIELDS if c not in fields]
            if missing:
                raise ValueError(f"필수 헤더 누락: {missing}")
            for row in reader:
                lv = (row.get("level") or "").strip()
                if lv not in ("WARN", "FAIL"):
                    raise ValueError(f"미등록 level: {lv!r} (허용: WARN/FAIL)")
                raw_idx = (row.get("index") or "").strip()
                try:
                    idx = int(raw_idx)
                except ValueError:
                    raise ValueError(f"index 정수 아님: {raw_idx!r}")
                details.append({
                    "scenario": (row.get("scenario") or "").strip(),
                    "index": idx,
                    "level": lv,
                    "reason": row.get("reason", ""),
                    "artifact": row.get("artifact_dir") or None,
                })
        return details

    def run(self):
        """반복은 하니스가 내부 수행 → 1회 호출 후 summary.txt 를 실집계로 수용."""
        print(f"\n{'='*54}\n[TEST] {self.name} (harness, -S {self.scenarios} -n {self.count})\n{'='*54}")

        # 요청 계약 (하니스 실행 전 차단): 빈 토큰·중복 시나리오·count<=0·예약 옵션
        tokens = [t.strip() for t in self.scenarios.split(",")]
        if not tokens or any(t == "" for t in tokens):
            return self._infra(
                f"요청 계약 위반: 빈 scenario 토큰 포함 — scenarios={self.scenarios!r}")
        if len(set(tokens)) != len(tokens):
            return self._infra(
                f"요청 계약 위반: 중복 시나리오 — (scenario,index) 순서 복원 불가: {tokens}")
        requested = tokens
        if self.count <= 0:
            return self._infra(f"요청 계약 위반: count={self.count} (count>0 필요)")
        bad_opts = [a for a in self.extra_args
                    if str(a) in RESERVED_HARNESS_OPTS
                    or str(a).split("=", 1)[0] in RESERVED_HARNESS_OPTS]
        if bad_opts:
            return self._infra(
                f"extra_args 예약 옵션 사용 금지 (wrapper 관리 영역): {bad_opts}")

        try:
            bash_path = resolve_bash(self.bash_path_cfg)
        except InfraFailure as e:
            return self._infra(f"bash resolve 실패: {e}")
        with open(os.path.join(self.run_dir, "bash_resolved.txt"), "w", encoding="utf-8") as f:
            f.write(bash_path + "\n")
        print(f"  [INFO] bash: {bash_path}")

        out_root = os.path.join(self.run_dir, "bug23025")
        cmd = [bash_path, HARNESS, "-S", self.scenarios, "-n", str(self.count),
               "-o", out_root, "--no-menu"]
        if self.device_id:
            cmd += ["-s", self.device_id]
        cmd += list(self.extra_args)

        try:
            rc = subprocess.run(cmd, env={**os.environ, "NO_COLOR": "1"}).returncode
        except (OSError, subprocess.SubprocessError) as e:
            return self._infra(f"하니스 실행 예외: {type(e).__name__}: {e}")

        latest = self._latest_run_dir(out_root)
        if latest is None:
            return self._infra(f"하니스 run directory 부재: {out_root}")

        summary_path = os.path.join(latest, "summary.txt")
        if not os.path.isfile(summary_path):
            return self._infra("summary.txt 부재 — 하니스 조기 종료 의심", latest)

        try:
            rows, total = parse_harness_summary(summary_path)
        except SummaryParseError as e:
            return self._infra(f"summary 파싱 실패/모순: {e}", latest)

        if total["count"] == 0:
            return self._infra("실행 회차 0건 (summary 합계 0)", latest)

        # 요청 대비 계약: 하니스는 미등록 시나리오를 warn 후 무시하므로(성공 위장 가능),
        # summary 행을 요청 목록과 순서·중복 포함 정확 대조 + 각 행 count == 요청 count.
        names = [r["name"] for r in rows]
        if names != requested:
            return self._infra(
                f"시나리오 계약 불일치: 요청 {requested} vs summary {names}", latest)
        mismatch = [(r["name"], r["count"]) for r in rows if r["count"] != self.count]
        if mismatch:
            return self._infra(
                f"회차 계약 불일치: 요청 count={self.count} vs summary {mismatch}", latest)

        # results.csv (scenario, index) 검증 — 미등록 scenario / index 범위 / 중복 = INFRA
        try:
            details = self._read_detail_rows(os.path.join(latest, "results.csv"))
        except ValueError as e:
            return self._infra(f"results.csv 파싱 실패: {e}", latest)

        by_pos = {}
        csv_counts = {name: {"WARN": 0, "FAIL": 0} for name in requested}
        for d in details:
            if d["scenario"] not in csv_counts:
                return self._infra(
                    f"results.csv 미등록 scenario: {d['scenario']!r} (요청 {requested})", latest)
            if not (1 <= d["index"] <= self.count):
                return self._infra(
                    f"results.csv index 범위 위반: {d['scenario']}#{d['index']}"
                    f" (유효 1..{self.count})", latest)
            key = (d["scenario"], d["index"])
            if key in by_pos:
                return self._infra(
                    f"results.csv 중복 index: {d['scenario']}#{d['index']}", latest)
            by_pos[key] = d
            csv_counts[d["scenario"]][d["level"]] += 1

        # 실제 회차 순서 복원: 요청 시나리오 순 × index 1..count.
        # csv 에 없는 index 만 PASS 로 복원 (미실행 PASS 추정 아님 — summary 와 재대조).
        ordered = []
        restored_pass = {name: 0 for name in requested}
        for name in requested:
            for idx in range(1, self.count + 1):
                d = by_pos.get((name, idx))
                if d is None:
                    ordered.append(("PASS", "", None))
                    restored_pass[name] += 1
                else:
                    ordered.append((d["level"], f"[{name}#{idx}] {d['reason']}", d["artifact"]))

        # 복원 후 summary 재대조 — 시나리오별 P/W/F 전부 일치해야 결과 수용
        for r in rows:
            name = r["name"]
            if (restored_pass[name] != r["pass"]
                    or csv_counts[name]["WARN"] != r["warn"]
                    or csv_counts[name]["FAIL"] != r["fail"]):
                return self._infra(
                    f"복원-재대조 불일치 [{name}]: 복원 P{restored_pass[name]}"
                    f"/W{csv_counts[name]['WARN']}/F{csv_counts[name]['FAIL']}"
                    f" vs summary P{r['pass']}/W{r['warn']}/F{r['fail']}", latest)

        self.results.extend(ordered)

        # 유효한 summary 와 process exit code 불일치 = INFRA_FAILURE 로 기록
        expect = 1 if total["fail"] else (2 if total["warn"] else 0)
        if rc != expect:
            self._infra(f"하니스 exit={rc}, summary 기준 기대 {expect} — 비정상 종료 의심", latest)
        return self.results
