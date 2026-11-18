"""Field-collection workbook commands.

    .\\.venv\\Scripts\\python.exe scripts\\field_data.py new                     (empty workbook to fill on site)
    .\\.venv\\Scripts\\python.exe scripts\\field_data.py build <filled workbook>  (model-ready dataset)
"""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.field_collection import create_workbook, write_dataset  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="Create an empty field-collection workbook")
    new.add_argument("--output", default=str(ROOT / "data" / "field_collection_workbook.xlsx"))
    build = sub.add_parser("build", help="Build the upload-ready dataset from a filled workbook")
    build.add_argument("workbook")
    build.add_argument("--output", default=str(ROOT / "data" / "recorded_dataset.xlsx"))
    args = parser.parse_args()
    try:
        if args.command == "new":
            print(f"Created {create_workbook(args.output)}")
            return 0
        dataset, exclusions, readiness = write_dataset(args.workbook, args.output)
    except (FileExistsError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Built {len(dataset)} rows -> {args.output} (and .csv); {len(exclusions)} passenger rows excluded.")
    print(readiness.to_string(index=False))
    if (readiness.Status != "OK").any():
        print("\nThe dataset imports now, but collect more where Status is not OK before final thesis results.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
