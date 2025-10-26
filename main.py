import logging
from log import debug, info, warn, error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main():
    logging.info("agent-starter")
    info({"project_name": "agent-starter"})


if __name__ == "__main__":
    main()
