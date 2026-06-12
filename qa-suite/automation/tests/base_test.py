# tests/base_test.py — 공통 베이스
# 원칙: FAIL/WARN 은 아티팩트 없이 존재할 수 없다. 판정은 프로세스 귀속 필수.
# 원칙: 인프라 실패(adb 불통·timeout·실행 파일 부재)는 "관찰 없음"이지 "이상 없음"이 아니다.
#       판정 경로의 인프라 실패는 INFRA_FAILURE 로 전파한다 (fail-closed).
import datetime
import os
import subprocess
import time
from dataclasses import dataclass

# 닫힌 execution outcome 집합 — 이 외 문자열은 전부 INFRA_FAILURE 처리
VALID_STATUSES = ("PASS", "WARN", "FAIL", "SKIP", "INFRA_FAILURE")


class InfraFailure(Exception):
    """판정 경로의 인프라 실패. PASS/FAIL 로 위장하지 않고 전파한다."""


@dataclass
class CommandResult:
    args: list
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool

    @property
    def ok(self) -> bool:
        return (not self.timed_out) and self.returncode == 0

    def brief(self) -> str:
        if self.timed_out:
            return f"timeout: {' '.join(map(str, self.args))}"
        return (f"rc={self.returncode}: {' '.join(map(str, self.args))}"
                f" stderr={self.stderr.strip()[:200]}")


class BaseTest:
    ADB = "adb"

    def __init__(self, config):
        self.repeat = int(config.get("repeat", 20))
        self.device_id = config.get("device_id", "") or ""
        self.run_dir = config["run_dir"]          # runner 가 주입 (logs/<run_id>)
        self.iter_gap = float(config.get("iter_gap", 2))
        self.name = self.__class__.__name__
        self.results = []                          # [(status, reason, artifact_dir|None)]
        os.makedirs(self.run_dir, exist_ok=True)

    # ---------- adb 헬퍼 (argv 기반, shell=False) ----------
    def _adb_argv(self, args):
        argv = [self.ADB]
        if self.device_id:
            argv += ["-s", self.device_id]
        return argv + list(args)

    def adb(self, args, timeout=30):
        """adb 실행. 항상 CommandResult 반환 — 실패를 빈 문자열로 바꾸지 않는다."""
        argv = self._adb_argv(args)
        try:
            r = subprocess.run(argv, shell=False, capture_output=True, timeout=timeout)
            return CommandResult(
                args=argv, returncode=r.returncode,
                stdout=(r.stdout or b"").decode("utf-8", errors="replace"),
                stderr=(r.stderr or b"").decode("utf-8", errors="replace"),
                timed_out=False,
            )
        except subprocess.TimeoutExpired as e:
            out = e.stdout or b""
            if isinstance(out, str):
                out = out.encode("utf-8", errors="replace")
            return CommandResult(args=argv, returncode=-1,
                                 stdout=out.decode("utf-8", errors="replace"),
                                 stderr="", timed_out=True)
        except (FileNotFoundError, OSError) as e:
            return CommandResult(args=argv, returncode=-1, stdout="",
                                 stderr=f"executable failure: {e}", timed_out=False)

    def adb_checked(self, args, timeout=30):
        """판정 경로 전용 — 실패 시 InfraFailure 전파."""
        r = self.adb(args, timeout=timeout)
        if not r.ok:
            raise InfraFailure(f"adb 판정 명령 실패 — {r.brief()}")
        return r

    def adb_shell(self, cmd, timeout=30):
        # 주의(Git Bash/MSYS): /sdcard 같은 경로 인자는 호스트 경로로 변환될 수 있음.
        # cmd 는 on-device 명령 문자열 그대로 단일 인자로 전달된다.
        return self.adb(["shell", cmd], timeout=timeout)

    def adb_binary(self, args, outfile, timeout=30):
        """바이너리 출력(adb exec-out 등)을 파일로 저장. 성공 여부 bool 반환."""
        argv = self._adb_argv(args)
        try:
            with open(outfile, "wb") as f:
                r = subprocess.run(argv, shell=False, stdout=f,
                                   stderr=subprocess.DEVNULL, timeout=timeout)
            return r.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def clear_logcat(self):
        self.adb_checked(["logcat", "-c"])

    # ---------- 대기: 고정 sleep 대신 상태 폴링 ----------
    def poll_until(self, predicate, timeout=10.0, interval=0.3):
        """predicate() 가 truthy 가 될 때까지 폴링. 성공 True / 타임아웃 False."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(interval)
        return False

    # ---------- 프로세스 귀속 판정 헬퍼 (실패 시 InfraFailure) ----------
    def pid_of(self, pkg):
        # pidof 는 미존재 프로세스에서 rc!=0 → on-device `|| true` 로 정상 관찰과 인프라 실패를 분리
        r = self.adb_checked(["shell", f"pidof {pkg} || true"])
        out = r.stdout.strip()
        return out.split()[0] if out else None

    def crashed(self, pkg, since_lines=400):
        """pkg 귀속 crash 만 True. 광역 예외 grep 금지 원칙의 구현체."""
        crash_buf = self.adb_checked(["logcat", "-b", "crash", "-d", "-t", str(since_lines)])
        if f"Process: {pkg}" in crash_buf.stdout:
            return True
        events = self.adb_checked(["logcat", "-b", "events", "-d", "-t", str(since_lines)])
        return any("am_crash" in ln and pkg in ln for ln in events.stdout.splitlines())

    def anr_of(self, pkg, since_lines=600):
        log = self.adb_checked(["logcat", "-d", "-t", str(since_lines)])
        return any(("ANR in" in ln or "Input dispatching timed out" in ln)
                   and pkg in ln for ln in log.stdout.splitlines())

    # ---------- 아티팩트 ----------
    def collect_artifacts(self, index, status, reason):
        ts = datetime.datetime.now().strftime("%H%M%S")
        d = os.path.join(self.run_dir, f"{status}_{self.name}_{index+1:04d}_{ts}")
        os.makedirs(d, exist_ok=True)
        errors = []

        if not self.adb_binary(["exec-out", "screencap", "-p"], os.path.join(d, "screen.png")):
            errors.append("screen.png: screencap 수집 실패")

        for fn, args in (("window.txt", ["shell", "dumpsys window"]),
                         ("activities.txt", ["shell", "dumpsys activity activities"]),
                         ("logcat_tail.txt", ["logcat", "-d", "-v", "threadtime", "-t", "3000"])):
            r = self.adb(args, timeout=60)
            with open(os.path.join(d, fn), "w", encoding="utf-8", errors="replace") as f:
                f.write(r.stdout)
            if not r.ok:
                errors.append(f"{fn}: {r.brief()}")

        with open(os.path.join(d, "context.txt"), "w", encoding="utf-8") as f:
            f.write(f"test      : {self.name}\n"
                    f"iteration : #{index+1} / {self.repeat}\n"
                    f"status    : {status}\nreason    : {reason}\n"
                    f"time      : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n"
                    f"serial    : {self.device_id or 'auto'}\n")

        try:
            self.extra_artifacts(d)
        except Exception as e:  # 버그 특이 수집 실패도 숨기지 않는다
            errors.append(f"extra_artifacts: {type(e).__name__}: {e}")

        if errors:
            with open(os.path.join(d, "collection_errors.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(errors) + "\n")
            print(f"  [WARN] artifact collection failure x{len(errors)} → {d}/collection_errors.txt")
        return d

    def extra_artifacts(self, artifact_dir):
        """버그 특이 아티팩트가 필요하면 오버라이드."""
        pass

    # ---------- 라이프사이클 ----------
    def setup(self): pass
    def teardown(self): pass

    def run_once(self, index):
        """반드시 오버라이드. return "PASS"|"SKIP" 또는 (status, reason). status 는 VALID_STATUSES 한정."""
        raise NotImplementedError

    @staticmethod
    def _normalize_outcome(out):
        """run_once 반환값 검증 — 닫힌 집합 밖이면 INFRA_FAILURE (PASS 로 계산 금지)."""
        if isinstance(out, str):
            status, reason = out, ""
        elif (isinstance(out, tuple) and len(out) == 2
              and isinstance(out[0], str) and isinstance(out[1], str)):
            status, reason = out
        else:
            return "INFRA_FAILURE", f"run_once 반환 형식 오류: {out!r}"
        if status not in VALID_STATUSES:
            return "INFRA_FAILURE", f"미등록 status 문자열: {status!r}"
        return status, reason

    def _safe_teardown(self):
        try:
            self.teardown()
        except Exception as e:
            # 원래 결과를 덮어쓰지 않고 추가 행으로 기록 (환경 정리 실패 = 인프라 이슈)
            self.results.append(("INFRA_FAILURE", f"teardown failure: {e}", None))

    def run(self):
        print(f"\n{'='*54}\n[TEST] {self.name}  (x{self.repeat})\n{'='*54}")
        try:
            self.setup()
        except Exception as e:
            self.results.append(("INFRA_FAILURE", f"setup failure: {e}", None))
            self._safe_teardown()
            return self.results

        try:
            for i in range(self.repeat):
                try:
                    out = self.run_once(i)
                except InfraFailure as e:
                    self.results.append(("INFRA_FAILURE", f"#{i+1}: {e}", None))
                    print(f"\n  [INFRA_FAILURE] #{i+1}: {e} → 잔여 회차 중단")
                    break
                except Exception as e:
                    self.results.append(
                        ("INFRA_FAILURE", f"#{i+1}: unhandled {type(e).__name__}: {e}", None))
                    print(f"\n  [INFRA_FAILURE] #{i+1}: {type(e).__name__}: {e} → 잔여 회차 중단")
                    break

                status, reason = self._normalize_outcome(out)
                if status == "INFRA_FAILURE":
                    self.results.append((status, f"#{i+1}: {reason}", None))
                    print(f"\n  [INFRA_FAILURE] #{i+1}: {reason} → 잔여 회차 중단")
                    break

                art = None
                if status in ("WARN", "FAIL"):
                    art = self.collect_artifacts(i, status, reason)
                    print(f"  [{status}] #{i+1}: {reason}  -> {art}")
                else:
                    print(f"\r  진행 {i+1}/{self.repeat}", end="")
                self.results.append((status, reason, art))
                time.sleep(self.iter_gap)
        finally:
            print()
            self._safe_teardown()
        return self.results
