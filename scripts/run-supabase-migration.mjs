import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";

import pg from "pg";

const { Client } = pg;

async function runSql(client, label, filePath) {
  const sql = await readFile(filePath, "utf8");
  if (!sql.trim()) {
    throw new Error(`SQL file is empty: ${filePath}`);
  }

  console.log(`Running ${label}: ${filePath}`);
  await client.query(sql);
}

async function verify(client) {
  const tableResult = await client.query(`
    select table_name
    from information_schema.tables
    where table_schema = 'public'
      and table_name in (
        'tenants',
        'users',
        'credits',
        'projects',
        'jobs',
        'credit_packs',
        'assets'
      )
    order by table_name;
  `);

  const seedResult = await client.query(`
    select
      (select count(*) from public.credit_packs) as credit_packs,
      (select count(*) from public.media_presets) as media_presets,
      (select count(*) from public.caption_presets) as caption_presets,
      (select count(*) from public.music_tracks) as music_tracks;
  `);

  console.log("Verified tables:", tableResult.rows.map((row) => row.table_name).join(", "));
  console.log("Seed counts:", seedResult.rows[0]);
}

async function main() {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is required.");
  }

  const schemaPath =
    process.argv[2] ??
    resolve("supabase", "migrations", "202603180001_initial_schema.sql");
  const seedPath =
    process.argv[3] ??
    resolve("supabase", "seed", "001_launch_seed.sql");

  const client = new Client({
    connectionString: databaseUrl,
    ssl: {
      rejectUnauthorized: false,
    },
  });

  await client.connect();

  try {
    await runSql(client, "schema", schemaPath);
    await runSql(client, "seed", seedPath);
    await verify(client);
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
