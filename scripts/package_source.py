"""Package the local web implementation, excluding dependencies and research data."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    root = Path(__file__).resolve().parents[1]
    destination = root / "thesis-mlr-source.zip"
    included = [root / name for name in (
        ".gitignore", "main.py", "Start MLR System.bat", "setup.ps1", "README.md",
        "requirements.txt", "requirements-lock.txt", "pytest.ini",
    )]
    for folder in ("src", "backend", "tests", "scripts", "docs"):
        included.extend(p for p in (root / folder).rglob("*") if p.is_file()
                        and "__pycache__" not in p.parts and p.name != "thesis-extracted.txt")
    for folder in ("src", "public", "tests", "dist"):
        included.extend(p for p in (root / "frontend" / folder).rglob("*") if p.is_file())
    included.extend(root / "frontend" / name for name in (
        "package.json", "package-lock.json", "tsconfig.json", "vite.config.ts", "index.html",
    ))
    included.extend(root / "data" / name for name in (
        "README.md", "transportation_template.csv", "transportation_template.xlsx",
        "recorded_observation_template.csv", "recorded_observation_template.xlsx",
    ))
    included.extend([root / "outputs" / ".gitkeep", root / "models" / ".gitkeep"])
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in sorted(set(included)):
            if path.is_file(): archive.write(path, path.relative_to(root))
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert "frontend/dist/index.html" in names and "backend/app/main.py" in names
        assert not any("desktop" in name or ".web-data/" in name or "node_modules/" in name for name in names)
    print(f"Packaged {len(names)} files: {destination} ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
