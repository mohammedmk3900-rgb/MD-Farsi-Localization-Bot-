import argparse
from app.runtime import build_application

def main() -> None:
    parser = argparse.ArgumentParser(prog="md-news-genesis")
    parser.add_argument("command", choices=["health", "events"])
    args = parser.parse_args()
    app = build_application()
    if args.command == "health":
        print(app.health.evaluate({"database": "ok"}))
    else:
        print(app.store.events())

if __name__ == "__main__":
    main()
