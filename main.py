from dotenv import load_dotenv
from cli import app


def main():
    load_dotenv()
    app()


if __name__ == "__main__":
    main()
