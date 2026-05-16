#!/usr/bin/env bash
set -xe

export UV_FROZEN=1

uv run --active prek run --all-files
uv run --active mypy

export URT30DISCORD_CONFIG_FILE=./tests/test_config.toml

uv run --active pytest -p no:cacheprovider
