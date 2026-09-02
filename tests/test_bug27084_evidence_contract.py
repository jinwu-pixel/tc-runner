import ast
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUG_ROOT = ROOT / "AT-M140 - Launcher BUG27084"
EVIDENCE_ROOT = BUG_ROOT / "evidence"
LEDGER_PATH = BUG_ROOT / "EVIDENCE_LEDGER.json"


EXPECTED_MANIFESTS = {
    "20260828T184716KST_z0611_baseline": "0075C650A425C5BD071B38E2B0885EBC21BD7D798511B5914FB937C6EE145C23",
    "20260828T190245KST_voc_sample_readonly": "5EA0C697D5B2AD9E5674958C4B6DAA42041D7608638B593ACA2FB15BB7EF42C7",
    "20260828T191249KST_v126_repro": "6D07E43361D9CC4C1DBA823D1D3554A4AC45C7822B0A8B618721A3E50B12DECA",
    "20260828T221502KST_widget_generality": "53306F644019EE361CFE13E404CC0116DC95E91CE42B88928032DC61AB33D0A8",
    "20260829T003741KST_nonweather_controls": "BA20030AF76C5E332FFEF6392DBB9DEC3702D52C4DE6A876E9EBDBFD2ED89F81",
    "20260831T055735Z": "8109A64591C9FF533134DE9C2D48087AEDA8956C3B0A8C6E32CBDECE80FBF366",
    "20260831T065419Z": "E893AA83310B0A31E147F4D6090F5242EF8D08DB5DD6E2350D4679D036304F84",
    "20260901T033937Z": "01FBD67BDEFB357D2E50A3C84B20B5D22214B1303FAC7C58CB99FB4EEE56AC48",
    "20260901T034040Z": "40932BC00A54631A1A75795B11E06A416EBBE93CDDE2F41FECA1D23B6F89D932",
    "20260901T034114Z": "EAEAAE8971455E80A450C3901FDE50874B808E91321FB61C361095338E256FBC",
    "20260901T035105Z": "0EEC5A5D6AB69D4A0E29FD03066C0B43C0BACABB4F7BD9EFD07A28B91932EEAE",
    "20260901T040059Z": "EE0153D5E1BC050ABB6EE1EBC99CB60AAF5BA936E7D5D42108BD5B124A18EE2E",
    "20260901T041058Z": "021F8D18ABD579C3D724E9A579F9D872C33C5B5D5486610858D86F725DC7454A",
    "20260901T041342Z": "FA67C02D26F6B0BC1CF0647F0BE618F133C98023367299FBD8F43966C6DBFD1B",
    "20260901T060745Z": "32D2547C59EF8DF0A5E52B3D8EC46C2D4C9D59E53EFDF0C77F562382AC534AF1",
    "20260901T061739Z": "82F33598CA69DBA161B1968D8F90AADB3C704F203849F129A20D047703EFA558",
    "20260901T075514Z": "8F7785E6544F5A3FC4613EE8B99722DBBECBBC1CD0D0F8C86298656BE427855A",
    "20260901T075920Z": "E6EC7F3AEB22568EFDFBAD5090D4CDA89B399CAAAFEAA282A9F50C130EC680B9",
    "20260901T115716Z": "01A5148170283A31CA8167F1B9107615579EB22BEB557E467B8BCC78A81B982C",
    "20260901T120902Z": "FC0EFD41E5E79213C957C3B493E8D1C51064B8058EA424781ABEC105C5344A9C",
    "20260901T121340Z": "60C0BD6CC4438076862CC26A4E1806D5794D8D08D370EE2808D1EBD609719563",
    "20260901T121834Z": "F2D24A7CF0862F32B8557B710D56A7C838E08F7B4E5ED97AD0518CA5BA5BE3D8",
    "20260901T122309Z": "8A20A25D64F2F96EBF744F7798DDD81B9E4AEE508D7E941E1389DB5D98DFBE50",
    "20260901T123656Z": "EF27D3722AF7AF698CE43C963A8FC8262D26F8F82957033B2226C61C168E88C6",
    "20260901T124535Z": "194AB890BA5778C6586A335CC9F7093F92360DEB5FACD747D31704CFB35A955D",
    "20260901T125328Z": "DEF73B1B06D07EE92AE0F9802332EE7EA8D49222E7C1444392AD79CB42075028",
    "20260901T130054Z": "45C82CF3AD83BBAD61AE9E33F6FD8F6EFF3145179975EF71EEA71F312746FFB8",
    "20260901T131524Z": "8DBB7DC8177268DE8EA9B39F232655EBD8F4ED920192185934AF2DEC75A36278",
    "20260901T134642Z": "E02374E5709219D09B1BD17E0CAACD7912879C8211A4DEFC841D7319BEFC8543",
    "20260901T135414Z": "90111BD950EA6461626DEC0FA9A66C90CF80ACB5D308530480D31D603C2D7383",
    "20260901T135852Z": "2A041CFFD77379B1DDF0B2D7756BAB4C7D81948BB826F72B0349B894DB08BC78",
    "20260901T140308Z": "ED7A4B909DC941274C3F1C16DEB22E0D65A10A9FADD5327D11A832476AE1C0DA",
    "20260901T141954Z": "277F854AEF82EE83332507A08FA38FA139282A8F7D44F9AC2F65A236F6A07789",
    "20260901T143225Z": "AD8D7D736E5133E5339C4A3CF81AB93868F50CC6561B3644608F1455786498A4",
    "20260901T143618Z": "BB1973FA7087184E98FF434A819DEECD1FB1D4613E22FCC19253F9290D5F87B9",
    "20260901T144017Z": "63C3FB4B2D8D5B0B1BEB1732BDE1553A306DA8E85A820EECCD8954A6C201D7CC",
    "20260901T144423Z": "1867FA344ED64E18A6D9955DCE54CCACBCC03D8AE98DD667688F9CE10EF2A95C",
    "20260901T145142Z": "8E987526F3ED5214F7833951327571C1ADFDBE13C5637CEAA42229BF08036A02",
    "20260901T145530Z": "421907EFB8D85E0477A49B9BE0984302675E1887CD918848BBFAD65559276D43",
    "20260901T145912Z": "D234DF073A28086AC1600871DD03878E9D7F2EAFEDF20B63341CA14F1F13A0D9",
    "20260901T150301Z": "0F7FFC1AFB3A6AB7708D487B24B07DC9C2DF86D3A3D7BC5D6E0114B088B51038",
    "20260901T150649Z": "7FE3DAC18B4128E44CD013794E7CCD8A431F473E8B10DE2D559A4F902DD41EA5",
    "20260901T151403Z": "A8396E367317D62D53A206EE224AFBECC273A5865BE8B2E769584C105C7BB885",
    "20260901T151737Z": "8CCCAD5D98A5A431BF20AF811CF8E8BCBF8B5E8AA1171173813CF01C86D695E0",
    "20260901T152148Z": "79003D10A04F54E8471DD8CD5CF0DFF922D946E5C784C7AE552F77A90BC9EC8A",
}


EXPECTED_LEGACY_TREES = {
    "20260828T184716KST_z0611_baseline": "8DACBE6FCBC6588532CD39D6667390B36CCBEE02532C4CF694098BCD3D715005",
    "20260828T190245KST_voc_sample_readonly": "88B822E9E55CBC99D952696FACF1F0D72E5B5E1BE708F8A114B4B3B4AE79B9AB",
    "20260828T191249KST_v126_repro": "798AE53FE98CF7947E70672549A5E15749F934CAD5C44131AB889CFF8658F273",
    "20260828T221502KST_widget_generality": "A1F9ADD2741E17286A1964988CBA528F19CE31CAF091AFEF7100C28B5CA43147",
    "20260829T003741KST_nonweather_controls": "A13D062E55AED16D4BD19982C4645192F6C27E14F0CE0A1B69996C32125F8D70",
    "20260831T055735Z": "2404F64D505AA4F6053D301B5BB9861FFB0B9029B3013B5E402A94D9C9334CDA",
    "20260831T065419Z": "E6AB0E7B64582AA50EA0116CCA97DB9A1417648D6CBF1956E1A01C517283F131",
    "20260901T033937Z": "F9C645BD79902413CC8B5B11D324AA82F457F888684C564839CF4ED19DE3778E",
    "20260901T034040Z": "8CEBD85307434A17C3A8E68C95F862AE06F4CBD0097496512610002C93227EA4",
    "20260901T034114Z": "C988EA8E6B57B97A09A139366D13052F2D086949C6D28C3E379341146D67F748",
    "20260901T035105Z": "8C289F7227222D4A669B61968784F8B33840999FA249F9C60140C8170CCD443A",
    "20260901T040059Z": "F6F29E46A599F91E9177F3EEDE923A020340C8EFC6ACCE72B87F298B56BE7C4D",
    "20260901T041058Z": "AD4FBF0FE55969516611231CA0ADA541E5BA5D0F9817AD51247AA606439909B7",
    "20260901T041342Z": "B4693D65EF1413F62527CEB74F7A99DF866F88DECF370B6EFFADE47F4842CFD8",
    "20260901T060745Z": "F3028390B047680CE6F7820D0288DD35FCF2FE1AD9674879EDCDB53F31A26B2C",
    "20260901T061739Z": "11AE52B0A3A1C20A912FCA29D2895AC7AA314566605B1AFD7DD49D8EBFD3A440",
    "20260901T075514Z": "CDFAEB606EF51434264EF4ABD44F2F6E3287FAB8B90AB4C715C99B3C73FA3706",
    "20260901T075920Z": "636DC971FEF3BBD624A9BEC82BEF0C82CA5A3235E0EC180CEE5D38683038CCB3",
    "20260901T115716Z": "4D8A522292EE8D21488B5D4FE05E6604153F596CC6FF8AA94D9BFA4EC3544D5F",
    "20260901T120902Z": "D02B1C66C9C533DBB7F2E8CAA8370435C7B4D615CD16E442686565ABCA3A9080",
    "20260901T121340Z": "D73ED387EAB1CA5DDF88F3A4B6F8B4AB2D75D020037AA9C6F7E720F7C148DD8B",
    "20260901T121834Z": "DB78E4BBBD37CB3CED34D66BF70AC6182FEAE2907D6B3A12734C9DABF24A9C91",
    "20260901T122309Z": "4582A67BCC83AD6DFB403B3487532C931360FC974AA28987C5DC8A969B914E35",
    "20260901T123656Z": "73EBADBC4A88D8C404F138CF586B6C4F122EF097A378AA9D7BFDD712126A0A88",
    "20260901T124535Z": "838FD0096D85C781E7C82A00690630CB733E73FD324B7E7436A368217A5E0FF2",
    "20260901T125328Z": "086882566A0773F43A9157E133572E4500A868927E0B1869BC218FCAAC89B072",
    "20260901T130054Z": "4188CAC4F8095683B82A296832595B04FCC17674C6F91CE98173C7C672639A97",
    "20260901T131524Z": "415886F9B1CDCD144CDA41FC416704425C04DF580BE03BFEE5C9FAAF7E5792D7",
    "20260901T134642Z": "34AC26EE97CDEA13116FDC025808FA3DF92CF9E299827AA1EC7C42DA40E8B5FA",
    "20260901T135414Z": "B2EB3CAE4E625CA0BF811785AFD37C43AA13E523B3D8E8125C23D6B48855566C",
    "20260901T135852Z": "F57B5EF31ED2A590CF312A66DDF28A59C03DDAB24016650F9B9B4F88637810ED",
    "20260901T140308Z": "D4F9EF770FD5A93F66AF6BB917B84B7DF1CEDD31F1CBF82FF28539B570A7E8D1",
    "20260901T141954Z": "4335B4D906CBBBCEEB1965EC4DA4F7E63C8D1C2C23A67205DACD21DBF4F64171",
    "20260901T143225Z": "C634CDB64D8680688E89D7004407D106423FD0557743DE9B892E8EF8DA8904E8",
    "20260901T143618Z": "E62F512CF0E316AF18B8DB608B2C3E79042AAD95E4B502B66A7F1F2E445C927D",
    "20260901T144017Z": "693DC9FA89C636815AB4CA8D928E41738C0F0128B99AD0F7C96E61A156A13999",
    "20260901T144423Z": "EDBC78BBA0FE6D4D83904B75F76EB0D93A8A77FE8ED04E4705B4B6E7D27D3EA8",
    "20260901T145142Z": "A0F94B5DA33E08FA4A67DBD65BEA8BDF8DE53DE75366C8411DBAA98984AB2378",
    "20260901T145530Z": "C947B66F70F0DF7B7D7C151492033DFD01652131874633A137712FC986E462A5",
    "20260901T145912Z": "E3647B14B891B42661853FDD2F1E475B2EA56FEA33A43DC2654771528CD0F301",
    "20260901T150301Z": "AE6563CAA543CC49692A3FFC0343CF829E28EE5553783DF77D958C0C71E665CB",
    "20260901T150649Z": "EF7505C5FB9764B2AF327445262A0151B9EA3CF2499DCBDC1FF64B17CB1B0FA7",
    "20260901T151403Z": "47C421FB80F1A3E7A6159465408B0A2E061FE4097E6710AC39BFF3BFA7E52130",
    "20260901T151737Z": "B56F48C2AC599B3991E23664DD187D54C9D1D94708D1DA2B46B4EC05F41C51FB",
    "20260901T152148Z": "326793E2356DCD16E6895ED9FADFE7E3C605A2A253A2E86E4F53E9ABFC62F8E4",
}


def _bundle_tree_sha256(bundle: Path) -> str:
    files = []
    paths = sorted(
        bundle.rglob("*"), key=lambda path: path.relative_to(bundle).as_posix()
    )
    for path in paths:
        assert not path.is_symlink(), f"bundle tree contains a symlink: {path}"
        assert not getattr(path, "is_junction", lambda: False)(), (
            f"bundle tree contains a junction: {path}"
        )
        if not path.is_file():
            continue
        relative = path.relative_to(bundle).as_posix()
        if relative == ".run.lock":
            continue
        assert relative != ".evidence_pending.json"
        assert not relative.endswith(".tmp")
        data = path.read_bytes()
        files.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(data).hexdigest().upper(),
                "size": len(data),
            }
        )
    payload = {"files": files, "schema_version": 1}
    canonical = (
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


def _canonical_evidence_manifest_bytes(bundle: Path) -> bytes:
    entries = {}
    for path in bundle.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(bundle).as_posix()
        if (
            relative
            in {"evidence_sha256.txt", ".evidence_pending.json", ".run.lock"}
            or relative.endswith(".tmp")
        ):
            continue
        entries[relative] = hashlib.sha256(path.read_bytes()).hexdigest().lower()
    return "".join(
        f"{digest}  {relative}\n"
        for relative, digest in sorted(entries.items())
    ).encode("utf-8")


def _verify_evidence_entries(
    evidence_root: Path, legacy_entries: list[dict], provenance_entries: list[dict]
) -> None:
    legacy_run_ids = [entry["run_id"] for entry in legacy_entries]
    provenance_run_ids = [entry["run_id"] for entry in provenance_entries]
    assert legacy_run_ids == sorted(legacy_run_ids)
    assert provenance_run_ids == sorted(provenance_run_ids)
    assert len(legacy_run_ids) == len(set(legacy_run_ids))
    assert len(provenance_run_ids) == len(set(provenance_run_ids))
    assert set(legacy_run_ids).isdisjoint(provenance_run_ids)
    assert all(
        entry["source_provenance_status"] == "RECORDED"
        and re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", entry["run_id"])
        and re.fullmatch(r"[0-9a-f]{40}", entry["harness_commit"])
        and re.fullmatch(r"[0-9A-F]{64}", entry["source_digest_sha256"])
        and re.fullmatch(r"[0-9A-F]{64}", entry["evidence_manifest_sha256"])
        and re.fullmatch(r"[0-9A-F]{64}", entry["bundle_tree_sha256"])
        for entry in provenance_entries
    )

    ledger_entries = [*legacy_entries, *provenance_entries]
    actual_run_ids = {
        path.name for path in evidence_root.iterdir() if path.is_dir()
    }
    assert actual_run_ids == {entry["run_id"] for entry in ledger_entries}
    for entry in ledger_entries:
        bundle = evidence_root / entry["run_id"]
        manifest = bundle / "evidence_sha256.txt"
        assert manifest.is_file()
        assert hashlib.sha256(manifest.read_bytes()).hexdigest().upper() == entry[
            "evidence_manifest_sha256"
        ]
        assert _bundle_tree_sha256(bundle) == entry["bundle_tree_sha256"]
        if entry["source_provenance_status"] == "RECORDED":
            assert manifest.read_bytes() == _canonical_evidence_manifest_bytes(bundle)
            recorded = json.loads(
                (bundle / "harness_provenance.json").read_text(encoding="utf-8")
            )
            assert recorded["harness_commit"] == entry["harness_commit"]
            assert recorded["source_digest_sha256"] == entry[
                "source_digest_sha256"
            ]


def test_bundle_tree_digest_detects_unmanifested_payload_change(tmp_path):
    bundle = tmp_path / "run"
    bundle.mkdir()
    (bundle / "evidence_sha256.txt").write_bytes(b"opaque legacy manifest\n")
    payload = bundle / "payload.bin"
    payload.write_bytes(b"before")
    original = _bundle_tree_sha256(bundle)

    payload.write_bytes(b"after!")
    assert _bundle_tree_sha256(bundle) != original

    (bundle / ".run.lock").write_bytes(b"operational lock bytes")
    without_lock = _bundle_tree_sha256(bundle)
    (bundle / ".run.lock").write_bytes(b"changed lock bytes")
    assert _bundle_tree_sha256(bundle) == without_lock


def _seed_future_provenance_bundle(tmp_path):
    evidence_root = tmp_path / "evidence"
    bundle = evidence_root / "20260902T010203Z"
    bundle.mkdir(parents=True)
    harness_commit = "a" * 40
    source_digest = "B" * 64
    (bundle / "harness_provenance.json").write_text(
        json.dumps(
            {
                "harness_commit": harness_commit,
                "source_digest_sha256": source_digest,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle / "payload.bin").write_bytes(b"future evidence")
    manifest = bundle / "evidence_sha256.txt"
    manifest.write_bytes(_canonical_evidence_manifest_bytes(bundle))
    entry = {
        "run_id": bundle.name,
        "evidence_manifest_sha256": hashlib.sha256(
            manifest.read_bytes()
        ).hexdigest().upper(),
        "bundle_tree_sha256": _bundle_tree_sha256(bundle),
        "source_provenance_status": "RECORDED",
        "harness_commit": harness_commit,
        "source_digest_sha256": source_digest,
    }
    return evidence_root, entry


def test_future_provenance_entry_is_accepted(tmp_path):
    evidence_root, entry = _seed_future_provenance_bundle(tmp_path)
    _verify_evidence_entries(evidence_root, [], [entry])


def test_future_provenance_entry_rejects_unledgered_bundle(tmp_path):
    evidence_root, entry = _seed_future_provenance_bundle(tmp_path)
    (evidence_root / "20260902T010204Z").mkdir()
    with pytest.raises(AssertionError):
        _verify_evidence_entries(evidence_root, [], [entry])


def test_future_provenance_entry_rejects_manifest_that_does_not_seal_payload(
    tmp_path,
):
    evidence_root, entry = _seed_future_provenance_bundle(tmp_path)
    bundle = evidence_root / entry["run_id"]
    manifest = bundle / "evidence_sha256.txt"
    manifest.write_bytes(b"not a file manifest\n")
    entry["evidence_manifest_sha256"] = hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest().upper()
    entry["bundle_tree_sha256"] = _bundle_tree_sha256(bundle)

    with pytest.raises(AssertionError):
        _verify_evidence_entries(evidence_root, [], [entry])


@pytest.mark.parametrize(
    "field,bad_value",
    (
        ("harness_commit", "c" * 40),
        ("source_digest_sha256", "D" * 64),
        ("evidence_manifest_sha256", "E" * 64),
        ("bundle_tree_sha256", "F" * 64),
    ),
)
def test_future_provenance_entry_rejects_digest_or_pair_mismatch(
    tmp_path, field, bad_value
):
    evidence_root, entry = _seed_future_provenance_bundle(tmp_path)
    entry[field] = bad_value
    with pytest.raises(AssertionError):
        _verify_evidence_entries(evidence_root, [], [entry])


@pytest.mark.parametrize("forbidden", (".evidence_pending.json", ".payload.tmp"))
def test_future_provenance_entry_rejects_pending_or_tmp_file(
    tmp_path, forbidden
):
    evidence_root, entry = _seed_future_provenance_bundle(tmp_path)
    (evidence_root / entry["run_id"] / forbidden).write_bytes(b"forbidden")
    with pytest.raises(AssertionError):
        _verify_evidence_entries(evidence_root, [], [entry])


def test_future_provenance_entry_rejects_symlink(tmp_path, monkeypatch):
    evidence_root, entry = _seed_future_provenance_bundle(tmp_path)
    sentinel = evidence_root / entry["run_id"] / "link-sentinel"
    sentinel.write_bytes(b"stand-in")
    original = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path == sentinel or original(path),
    )
    with pytest.raises(AssertionError, match="symlink"):
        _verify_evidence_entries(evidence_root, [], [entry])


def test_bug27084_evidence_ledger_is_exact_and_locally_verified_when_present():
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    assert ledger["schema_version"] == 2
    assert ledger["evidence_root"] == "AT-M140 - Launcher BUG27084/evidence"
    assert ledger["historical_bundle_policy"] == "BYTE_IMMUTABLE"
    assert ledger["tree_digest_contract"] == {
        "schema_version": 1,
        "algorithm": "SHA-256",
        "scope": (
            "all regular files recursively except root .run.lock, including "
            "evidence_sha256.txt"
        ),
        "path_style": "POSIX bundle-relative",
        "order": "path ascending",
        "file_record_fields": ["path", "sha256", "size"],
        "file_sha256_case": "UPPER",
        "canonical_json": (
            "UTF-8; ensure_ascii=false; sort_keys=true; separators=(',',':'); "
            "one trailing LF"
        ),
    }
    assert ledger["legacy_baseline"]["expected_count"] == 45
    assert ledger["legacy_baseline"]["manifest_policy"] == (
        "opaque bytes; do not parse or normalize legacy formats"
    )
    legacy_entries = ledger["legacy_baseline"]["entries"]
    legacy_run_ids = [entry["run_id"] for entry in legacy_entries]
    assert legacy_run_ids == sorted(legacy_run_ids)
    assert len(legacy_run_ids) == len(set(legacy_run_ids)) == 45
    assert {
        entry["run_id"]: entry["evidence_manifest_sha256"]
        for entry in legacy_entries
    } == EXPECTED_MANIFESTS
    assert {
        entry["run_id"]: entry["bundle_tree_sha256"]
        for entry in legacy_entries
    } == EXPECTED_LEGACY_TREES
    assert all(
        entry["source_provenance_status"] == "NOT_RECORDED_LEGACY"
        for entry in legacy_entries
    )
    assert all(re.fullmatch(r"[0-9A-F]{64}", entry["bundle_tree_sha256"])
               for entry in legacy_entries)

    provenance_entries = ledger["provenance_entries"]

    if not EVIDENCE_ROOT.exists():
        assert ledger["clean_clone_note"].startswith("NOTE:")
        return

    _verify_evidence_entries(EVIDENCE_ROOT, legacy_entries, provenance_entries)


def test_appwidget_repro_test_has_no_same_block_unreachable_statements():
    path = ROOT / "tests/test_appwidget_stale_provider_repro.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    unreachable = []
    terminators = (ast.Return, ast.Raise, ast.Break, ast.Continue)
    for node in ast.walk(tree):
        for _field, value in ast.iter_fields(node):
            if not isinstance(value, list) or not value:
                continue
            if not all(isinstance(item, ast.stmt) for item in value):
                continue
            terminated = False
            for statement in value:
                if terminated:
                    unreachable.append(statement.lineno)
                if isinstance(statement, terminators):
                    terminated = True
    assert unreachable == []


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_bug27084_operational_docs_and_results_are_bidirectionally_linked():
    required = (
        "BUG_LOG.md",
        "RESUME.md",
        "MENU_TREE.md",
        "HANDOFF_2026-09-02_SESSION_B_FIXED_BUILD.md",
    )
    assert all((BUG_ROOT / name).is_file() for name in required)

    result_28 = _text(BUG_ROOT / "RESULT_2026-08-28.md")
    result_29 = _text(BUG_ROOT / "RESULT_2026-08-29.md")
    result_01 = _text(BUG_ROOT / "RESULT_2026-09-01.md")
    assert "RESULT_2026-08-29.md" in result_28
    assert "RESULT_2026-08-28.md" in result_29
    assert "RESULT_2026-09-01.md" in result_29
    assert "RESULT_2026-08-29.md" in result_01
    assert all("EVIDENCE_LEDGER.json" in value for value in (result_28, result_29, result_01))
    assert "HANDOFF_2026-09-02_SESSION_B_FIXED_BUILD.md" in result_01


def test_bug27084_status_docs_pin_current_safe_state_and_session_b_gate():
    bug_log = _text(BUG_ROOT / "BUG_LOG.md")
    resume = _text(BUG_ROOT / "RESUME.md")
    menu_tree = _text(BUG_ROOT / "MENU_TREE.md")
    handoff = _text(BUG_ROOT / "HANDOFF_2026-09-02_SESSION_B_FIXED_BUILD.md")
    assert (
        "| ID | 기능 영역 | 진단 상태 | 이슈 상태 | 요약 | 관련 TC | 증거 |"
        in bug_log
    )
    assert all(
        marker in bug_log
        for marker in (
            "OBSERVED",
            "IN_PROGRESS",
            "fixed build",
            "- 기능 영역:",
            "- 진단 상태:",
            "- 이슈 상태:",
            "- 단말:",
            "- 앱:",
            "- 요약:",
            "- 기대 결과:",
            "- 실제 결과:",
            "- 재현 절차:",
            "- 관련 TC:",
            "- 증거:",
            "- 정정 이력:",
            "## 세션 결과",
            "- 실행일:",
            "- 범위:",
            "- PASS:",
            "- 신규 발견:",
            "- 변경·정정:",
            "- 다음 확인 항목:",
        )
    )
    assert all(
        marker in resume
        for marker in (
            "B06201249E00030C",
            "RY07260901S",
            "RESTORED_SAFE",
            "com.hnlens.simplemode",
            "45",
            "EVIDENCE_LEDGER.json",
        )
    )

    assert all(marker in menu_tree for marker in ("일반모드", "간편모드", "위젯"))
    digest = re.search(r"source_digest_sha256:\s*`([0-9A-F]{64})`", handoff)
    assert digest is not None

    provenance_path = ROOT / "scripts/appwidget_stale_provider_provenance.py"
    spec = importlib.util.spec_from_file_location(
        "bug27084_handoff_provenance", provenance_path
    )
    assert spec is not None and spec.loader is not None
    provenance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(provenance)
    try:
        actual_digest = provenance.inspect_harness(ROOT)[
            "source_digest_sha256"
        ]
    except provenance.HarnessProvenanceError:
        tracked = subprocess.run(
            (
                "git",
                "ls-files",
                "--error-unmatch",
                "--",
                "scripts/appwidget_stale_provider_provenance.py",
            ),
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if tracked.returncode == 0:
            raise
        # Before the candidate commit, emulate Git's text clean filter.  After
        # commit this branch is not used: inspect_harness reads HEAD blobs.
        files = []
        for relative in provenance.HARNESS_PATHS:
            data = ROOT.joinpath(*relative.split("/")).read_bytes().replace(
                b"\r\n", b"\n"
            )
            files.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(data).hexdigest().upper(),
                    "size": len(data),
                }
            )
        actual_digest = hashlib.sha256(
            provenance.canonical_source_bytes(files)
        ).hexdigest().upper()
    assert digest.group(1) == actual_digest
    assert "candidate commit OID는 commit 후" in handoff
    assert all(
        marker in handoff
        for marker in (
            "fixed build",
            "bootstrap-only",
            "Session B preparation commit",
            "campaign authority pair",
            "test_anchor_corpus_audit.py::test_corpus_file_counts_decomposed",
            "test_anchor_corpus_audit.py::test_audit_matches_golden_snapshot",
            "test_canonical_shell_rc_remediation.py::test_live_worktree_is_fully_remediated",
            "harness_commit + source_digest_sha256",
            "EVIDENCE_LEDGER.json",
            "ADB",
        )
    )


def test_source_of_truth_records_implemented_and_pending_boundaries():
    claude = _text(ROOT / "CLAUDE.md")
    design = _text(
        ROOT
        / "docs/superpowers/specs/2026-08-29-appwidget-stale-provider-knowledge-pipeline-design.md"
    )
    plan = _text(
        ROOT
        / "docs/superpowers/plans/2026-08-29-appwidget-stale-provider-knowledge-pipeline.md"
    )
    assert all(
        marker in claude
        for marker in (
            "appwidget_stale_provider_repro.py",
            "appwidget_stale_provider_provenance.py",
            "harness_commit + source_digest_sha256",
        )
    )
    assert all(
        marker in design
        for marker in (
            "Harness provenance amendment",
            "POSIX repo-relative",
            "fixture_reset schema v3",
            "lineage schema v2",
            "restore_provenance_<attempt>.json",
        )
    )
    assert all(
        marker in plan
        for marker in (
            "Implementation status reconciliation",
            "Tasks 4–10",
            "IMPLEMENTED",
            "Tasks 15–17",
            "BLOCKED",
            "docs/appwidget_stale_provider_verification.md",
            "NOT IMPLEMENTED",
        )
    )
