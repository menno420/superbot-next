-- 0011: CLEANUP store (band 2 slice 2) — the shipped word-filter list.
CREATE TABLE IF NOT EXISTS prohibited_words (
    guild_id BIGINT NOT NULL,
    word     TEXT   NOT NULL,
    PRIMARY KEY (guild_id, word)
);
