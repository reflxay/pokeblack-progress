"""Export public progress metadata from a clean, matching pokeblack main build."""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import struct
import tarfile
from datetime import datetime, timezone
from pathlib import Path

PROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
MATCH_LINES = ("main.sbin matches black.us/main.sha1", "arm7.sbin matches arm7.sha1",
               "ROM matches black.us/rom.sha1")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args],
        stderr=subprocess.STDOUT, timeout=60, creationflags=PROCESS_FLAGS,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"})


def receipt_verifies(proof, revision):
    # A base or worker SHA appearing in a receipt is not its verified main SHA.
    recorded = re.search(r"(?m)^\s*(?:integrated_commit|verified_main|main_sha|main_commit):\s*([0-9a-f]{40})\s*$", proof)
    return bool(recorded and recorded[1] == revision and all(line in proof for line in MATCH_LINES))


def read_receipt(path):
    proof = path.read_text(encoding="utf-8")
    log = re.search(r"(?m)^\s*compare_log:\s*(.+?)\s*$", proof)
    if log and not all(line in proof for line in MATCH_LINES):
        compare_log = Path(log[1])
        if not compare_log.is_absolute():
            compare_log = path.parent / compare_log
        if not compare_log.is_file():
            # A moved checkout may retain a copy beside the receipt.
            compare_log = path.parent / compare_log.name
        if compare_log.is_file():
            proof += "\n" + compare_log.read_text(encoding="utf-8", errors="replace")
    return proof


def sha1(path):
    digest = hashlib.sha1()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assembly_names(text):
    return re.findall(r"^\s*(?:thumb|arm)_func_start\s+(\w+)", text, re.M)


def has_assembly(text):
    return bool(re.search(r"\bGLOBAL_ASM\s*\(|\basm\s*(?:\{|\w+\s+\w+\s*\()|\b__asm\b", text))


def export(repo, objdiff, output, receipt):
    revision = git(repo, "rev-parse", "HEAD").decode().strip()
    if git(repo, "status", "--porcelain").strip():
        raise ValueError("Use a clean verified checkout; preserve worker edits.")
    if revision != git(repo, "rev-parse", "main").decode().strip():
        raise ValueError("Snapshot must be the verified main revision.")
    proof = read_receipt(receipt)
    if not receipt_verifies(proof, revision):
        raise ValueError("Provide the successful integration receipt for this main revision.")
    build = repo / "build/black.us"
    expected_main = (repo / "black.us/main.sha1").read_text().split()[0]
    expected_rom = (repo / "black.us/rom.sha1").read_text().split()[0]
    expected_arm7 = (repo / "sub/arm7.sha1").read_text().split()[0]
    with (build / "pokeblack.us.nds").open("rb") as rom:
        header = rom.read(0x40)
        offset, size = struct.unpack_from("<I", header, 0x30)[0], struct.unpack_from("<I", header, 0x3C)[0]
        rom.seek(offset)
        arm7_hash = hashlib.sha1(rom.read(size)).hexdigest()
    checks = {
        "arm9": sha1(build / "main.sbin") == expected_main,
        "arm7": arm7_hash == expected_arm7,
        "rom": sha1(build / "pokeblack.us.nds") == expected_rom,
    }
    if not all(checks.values()):
        raise ValueError("ARM9, ARM7 and full ROM must all match before export.")
    archive = git(repo, "archive", revision, "main.lsf", "src", "asm")
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        sources = {m.name: bundle.extractfile(m).read().decode("utf-8", "replace")
                   for m in bundle if m.isfile()}
    cache = output.parent.parent / ".cache"
    cache.mkdir(exist_ok=True)
    units, seen, module = [], set(), "main"
    for line in sources["main.lsf"].splitlines():
        header = re.match(r"^(?:Static|Overlay|Autoload)\s+(\w+)", line)
        if header:
            module = header[1]
        match = re.match(r"\s*Object\s+((?:src|asm)/[^\s]+\.o)(.*)", line)
        if not match or "(.bss)" in match[2] or match[1] in seen:
            continue
        obj = match[1]
        seen.add(obj)
        source = str(Path(obj).with_suffix(".c" if obj.startswith("src/") else ".s")).replace("\\", "/")
        text = sources[source]
        complete = obj.startswith("src/") and not has_assembly(text)
        path = build / obj
        if not path.is_file():
            raise ValueError(f"Missing built object: {obj}")
        unit = {"name": f"{module}/{obj[:-2]}", "target_path": str(path),
                "metadata": {"complete": complete}}
        if complete:
            unit["base_path"] = str(path)
        units.append(unit)
    (cache / "objdiff.json").write_text(json.dumps({"min_version": "2.0.0",
        "build_target": False, "build_base": False, "units": units}), encoding="utf-8")
    subprocess.run([str(objdiff), "report", "generate", "-p", str(cache),
                    "-o", str(cache / "report.json")], check=True, timeout=90,
                    creationflags=PROCESS_FLAGS, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    report = json.loads((cache / "report.json").read_text())
    # Only count emitted functions. This excludes force-export helpers discarded by the linker.
    emitted, module = {}, None
    for line in (build / "main.elf.xMAP").read_text(errors="replace").splitlines():
        header = re.match(r"# \.(\w+)\s*$", line)
        if header:
            module = header[1]
        match = re.match(r"\s+([\dA-Fa-f]{8}) ([\dA-Fa-f]{8}) \.text\s+(\S+)\s+\(([^()]+)\)", line)
        if match and module:
            obj = match[4].strip().split()[-1].lower()
            emitted[(module, obj, match[3].lower())] = (int(match[1], 16), int(match[2], 16))
    files, functions = [], []
    for unit in report["units"]:
        module, obj = unit["name"].split("/", 1)
        source = str(Path(obj).with_suffix(".c" if obj.startswith("src/") else ".s")).replace("\\", "/")
        basename = Path(obj).name.lower() + ".o"
        emitted_functions = [fn for fn in unit.get("functions", [])
            if (module, basename, fn["name"].lower()) in emitted]
        code = sum(int(fn["size"]) for fn in emitted_functions)
        complete = unit.get("metadata", {}).get("complete", False)
        index = len(files)
        files.append({"path": source, "module": module, "code": code,
                      "matched": code if complete else 0, "complete": complete})
        if source.startswith("asm/"):
            names = assembly_names(sources[source])
            for name in names:
                symbol = emitted.get((module, basename, name.lower()))
                if symbol:
                    functions.append({"name": name, "address": f"0x{symbol[0]:08X}",
                                      "size": None, "file": index, "status": "assembly"})
        else:
            for fn in emitted_functions:
                if fn["name"].startswith(("_@", "$")):
                    continue
                symbol = emitted[(module, basename, fn["name"].lower())]
                functions.append({"name": fn["name"], "address": f"0x{symbol[0]:08X}",
                    "size": int(fn["size"]), "file": index,
                    "status": "matched" if complete else "assembly"})
    modules = []
    for name in dict.fromkeys(f["module"] for f in files):
        members = [f for f in files if f["module"] == name]
        ids = {i for i, f in enumerate(files) if f["module"] == name}
        fns = [fn for fn in functions if fn["file"] in ids]
        modules.append({"name": name, "code": sum(f["code"] for f in members),
            "matched": sum(f["matched"] for f in members), "functions": len(fns),
            "matched_functions": sum(fn["status"] == "matched" for fn in fns)})
    data = {"revision": revision, "updated": datetime.now(timezone.utc).isoformat(),
        "verified": checks, "code": sum(f["code"] for f in files),
        "matched": sum(f["matched"] for f in files), "modules": modules,
        "files": files, "functions": functions}
    validate(data)
    if revision != git(repo, "rev-parse", "HEAD").decode().strip() or git(repo, "status", "--porcelain").strip():
        raise ValueError("Checkout changed during export; rerun at a clean boundary.")
    output.parent.mkdir(exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    temporary.replace(output)
    print(f"{revision[:8]}: {data['matched']:,}/{data['code']:,} code bytes; "
          f"{sum(fn['status'] == 'matched' for fn in functions):,}/{len(functions):,} named functions")


def validate(data):
    assert 0 <= data["matched"] <= data["code"]
    assert data["code"] == sum(m["code"] for m in data["modules"])
    assert data["matched"] == sum(m["matched"] for m in data["modules"])
    assert len(data["functions"]) == sum(m["functions"] for m in data["modules"])
    assert all(0 <= fn["file"] < len(data["files"]) for fn in data["functions"])
    assert all(fn["status"] != "matched" or data["files"][fn["file"]]["complete"] for fn in data["functions"])
    assert all(data["verified"].values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--objdiff", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data/progress.json")
    args = parser.parse_args()
    if args.check:
        assert assembly_names("\tthumb_func_start FUN_A\n\tarm_func_start FUN_B") == ["FUN_A", "FUN_B"]
        assert has_assembly("asm void f(void) {}") and has_assembly("void f() { asm { } }")
        assert not has_assembly("void f(void) { return; }")
        proof = "integrated_commit: " + "a" * 40 + "\nbase_main: " + "b" * 40 + "\n" + "\n".join(MATCH_LINES)
        assert receipt_verifies(proof, "a" * 40)
        assert not receipt_verifies(proof, "b" * 40)
        assert not receipt_verifies(proof.replace(MATCH_LINES[-1], "ROM mismatch"), "a" * 40)
        validate(json.loads(args.output.read_text()))
        print("Snapshot checks passed")
    else:
        if not args.repo or not args.objdiff or not args.receipt:
            parser.error("--repo, --objdiff and --receipt are required for export")
        export(args.repo.resolve(), args.objdiff.resolve(), args.output.resolve(), args.receipt.resolve())
