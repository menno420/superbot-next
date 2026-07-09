-- 0020: CHECKPOINT-GAME stores (band 6 slice 2) — shipped shapes carried
-- forward (090 chicken_farm, 077 creature_collection_log,
-- 082 creature_battle_record, mining_inventory + 061 mining_player_state,
-- 075/095 fishing_catch_log). Timestamps as BIGINT epochs (band convention);
-- mining user ids are TEXT in the shipped tables (kept — NAME_STABLE).

CREATE TABLE IF NOT EXISTS chicken_farm (
    user_id          BIGINT  NOT NULL,
    guild_id         BIGINT  NOT NULL DEFAULT 0,
    chickens         INTEGER NOT NULL DEFAULT 1,
    eggs             INTEGER NOT NULL DEFAULT 0,
    eggs_updated_at  BIGINT  NOT NULL DEFAULT 0,
    coop_level       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS creature_collection_log (
    user_id      BIGINT  NOT NULL,
    guild_id     BIGINT  NOT NULL DEFAULT 0,
    creature     TEXT    NOT NULL,
    count        INTEGER NOT NULL DEFAULT 0,
    first_caught BIGINT  NOT NULL,
    last_caught  BIGINT  NOT NULL,
    PRIMARY KEY (user_id, guild_id, creature)
);

CREATE TABLE IF NOT EXISTS creature_battle_record (
    user_id     BIGINT NOT NULL,
    guild_id    BIGINT NOT NULL DEFAULT 0,
    wins        INTEGER NOT NULL DEFAULT 0,
    losses      INTEGER NOT NULL DEFAULT 0,
    last_battle BIGINT NOT NULL,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS mining_inventory (
    user_id   TEXT    NOT NULL,
    guild_id  BIGINT  NOT NULL DEFAULT 0,
    item_name TEXT    NOT NULL,
    quantity  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id, item_name)
);

CREATE TABLE IF NOT EXISTS mining_player_state (
    user_id    TEXT    NOT NULL,
    guild_id   BIGINT  NOT NULL,
    depth      INTEGER NOT NULL DEFAULT 0,
    updated_at BIGINT  NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS fishing_catch_log (
    user_id      BIGINT NOT NULL,
    guild_id     BIGINT NOT NULL DEFAULT 0,
    species      TEXT   NOT NULL,
    count        INTEGER NOT NULL DEFAULT 0,
    best_weight  REAL   NOT NULL DEFAULT 0,
    total_value  BIGINT NOT NULL DEFAULT 0,
    first_caught BIGINT NOT NULL,
    last_caught  BIGINT NOT NULL,
    PRIMARY KEY (user_id, guild_id, species)
);
