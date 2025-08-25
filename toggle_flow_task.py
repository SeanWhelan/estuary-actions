#!/usr/bin/env python3
import argparse
import pathlib
import re
import subprocess
import sys
import tempfile


def pull_specs(name: str, work_dir: pathlib.Path) -> None:
    subprocess.run(
        ["flowctl", "catalog", "pull-specs", "--name", name, "--overwrite"],
        cwd=work_dir,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def find_spec_file(name: str, work_dir: pathlib.Path) -> pathlib.Path:
    yaml_files = list(work_dir.rglob("*.yaml"))
    name_pattern = re.compile(rf"^\s*{re.escape(name)}\s*:\s*$", re.M)
    for p in yaml_files:
        text = p.read_text()
        if name_pattern.search(text) and re.search(r"^(captures|materializations|collections):\s*$", text, re.M):
            return p
    for p in yaml_files:
        if name_pattern.search(p.read_text()):
            return p
    raise FileNotFoundError(f"Spec '{name}' not found in pulled YAML files")


def toggle_disable_in_file(name: str, spec_path: pathlib.Path, disable: bool) -> None:
    text = spec_path.read_text()
    name_pattern = re.compile(rf"^\s*{re.escape(name)}\s*:\s*$", re.M)
    m = name_pattern.search(text)
    if not m:
        raise RuntimeError("Spec header not found in file unexpectedly")

    lines = text.splitlines(True)
    # locate start index
    pos = 0
    start_idx = None
    for i, ln in enumerate(lines):
        if pos == m.start():
            start_idx = i
            break
        pos += len(ln)
    if start_idx is None:
        raise RuntimeError("Failed to compute block start index")

    # Determine indentation based on the header line
    header_line = lines[start_idx]
    header_indent = re.match(r"^(\s*)", header_line).group(1)
    # Children are one indent level deeper (Flow specs commonly use 2-space indents)
    child_indent = header_indent + "  "

    # find end of block (next peer under the same parent indentation)
    end_idx = None
    for j in range(start_idx + 1, len(lines)):
        ln = lines[j]
        if ln.startswith(header_indent) and not ln.startswith(child_indent) and ln.strip():
            end_idx = j
            break
    if end_idx is None:
        end_idx = len(lines)

    block = "".join(lines[start_idx:end_idx])

    shards_header_re = re.compile(rf"^{re.escape(child_indent)}shards:\s*$", re.M)
    disable_re = re.compile(rf"^{re.escape(child_indent)}  disable:\s*\S+", re.M)

    # Always relocate shards to the end of the mapping while preserving other shard settings
    block_lines = block.splitlines(True)
    # Locate existing shards section within the block, if any
    start_shards_idx = None
    end_shards_idx = None
    for idx, ln in enumerate(block_lines):
        if re.match(rf"^{re.escape(child_indent)}shards:\s*$", ln):
            start_shards_idx = idx
            # find the end where a sibling key starts (same child indent but not further indented)
            for j in range(idx + 1, len(block_lines)):
                l2 = block_lines[j]
                if l2.startswith(child_indent) and not l2.startswith(child_indent + " ") and l2.strip():
                    end_shards_idx = j
                    break
            if end_shards_idx is None:
                end_shards_idx = len(block_lines)
            break

    desired_disable_line = f"{child_indent}  disable: {'true' if disable else 'false'}\n"

    if start_shards_idx is not None:
        # Extract existing shards block and update/insert disable line
        shards_block = block_lines[start_shards_idx:end_shards_idx]
        # Determine if disable exists
        found_disable = False
        for k in range(1, len(shards_block)):
            if re.match(rf"^{re.escape(child_indent)}  disable:\s*\S+", shards_block[k]):
                shards_block[k] = desired_disable_line
                found_disable = True
                break
        if not found_disable:
            # Append disable after shards header
            shards_block.insert(1, desired_disable_line)
        # Remove the original shards block from block_lines
        del block_lines[start_shards_idx:end_shards_idx]
        # Ensure trailing newline on remaining block before appending
        if len(block_lines) and not block_lines[-1].endswith("\n"):
            block_lines[-1] = block_lines[-1] + "\n"
        # Append the preserved-and-updated shards block at the end
        block_lines.extend(shards_block)
    else:
        # No shards block existed: append a new one at the end
        if len(block_lines) and not block_lines[-1].endswith("\n"):
            block_lines[-1] = block_lines[-1] + "\n"
        block_lines.append(f"{child_indent}shards:\n")
        block_lines.append(desired_disable_line)

    # Remove any child-level expectPubId entries under this mapping, which block publication
    filtered_lines = []
    for ln in block_lines:
        if re.match(rf"^{re.escape(child_indent)}expectPubId:\s*\S+", ln):
            continue
        filtered_lines.append(ln)
    block_lines = filtered_lines

    block = "".join(block_lines)

    new_text = "".join(lines[:start_idx]) + block + "".join(lines[end_idx:])
    spec_path.write_text(new_text)


def show_snippet(spec_path: pathlib.Path) -> None:
    for ln in spec_path.read_text().splitlines():
        if ln.strip().startswith("shards:") or ln.strip().startswith("disable:"):
            print(ln)


def validate(work_dir: pathlib.Path, tolerate_failure: bool) -> None:
    try:
        subprocess.run(["flowctl", "catalog", "test", "--source", "flow.yaml"], cwd=work_dir, check=True)
        print("flowctl test: PASSED")
    except subprocess.CalledProcessError as e:
        if tolerate_failure:
            print("flowctl test: FAILED (tolerated)\n", file=sys.stderr)
        else:
            raise


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="Catalog name, e.g. org/namespace/task")
    ap.add_argument("action", choices=["disable", "enable"], help="Action to perform")
    ap.add_argument("--tolerate-test-failure", action="store_true", help="Do not exit non-zero if flowctl test fails")
    args = ap.parse_args()

    work_dir = pathlib.Path(tempfile.mkdtemp(prefix="flow-specs-", dir="/Users/sean/dev/estuary-test"))
    print(f"Working directory: {work_dir}")

    pull_specs(args.name, work_dir)
    spec_file = find_spec_file(args.name, work_dir)
    print(f"Spec file: {spec_file}")

    toggle_disable_in_file(args.name, spec_file, disable=(args.action == "disable"))
    show_snippet(spec_file)
    validate(work_dir, tolerate_failure=args.tolerate_test_failure)

    print(f"To publish: flowctl catalog publish --source '{work_dir}/flow.yaml'")

if __name__ == "__main__":
    main()
