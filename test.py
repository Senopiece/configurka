# --- main: parse file, restore and verify equality ---
import sys
from lark import UnexpectedInput

from parser import parse_configurik


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input_file>")
        sys.exit(1)
    filename = sys.argv[1]
    try:
        with open(filename, "r", encoding="utf-8") as f:
            input_data = f.read()
    except IOError as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    try:
        ast = parse_configurik(input_data)
    except UnexpectedInput as e:
        print("Parsing failed!")
        print(f"Line {e.line}, Column {e.column}:")
        print(e.get_context(input_data))
        print(f"Error type: {type(e).__name__}")
        sys.exit(1)

    if hasattr(ast, "pretty"):
        print("----- AST -----")
        print(ast.pretty())
    else:
        # Restore source from AST
        restored = ast.restore()
        identical = restored == input_data

        if not identical:
            print("----- ORIGINAL -----")
            print(input_data)
            print("----- RESTORED -----")
            print(restored)
            # exit non-zero on mismatch
            sys.exit(2)
        else:
            print("Restore successful and identical to original.")


if __name__ == "__main__":
    main()
