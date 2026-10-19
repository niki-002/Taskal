#!/bin/bash
# テスト用DBを作成する（DBボリュームの初回作成時のみ実行される）
# DB名は TEST_DATABASE_URL から取り出し、未設定なら「POSTGRES_DB_test」とする
set -euo pipefail

test_db="${TEST_DATABASE_URL:-}"
test_db="${test_db##*/}"
test_db="${test_db%%\?*}"
test_db="${test_db:-${POSTGRES_DB}_test}"

echo "Creating test database: ${test_db}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v test_db="$test_db" -v owner="$POSTGRES_USER" <<-'SQL'
	CREATE DATABASE :"test_db" OWNER :"owner";
SQL
