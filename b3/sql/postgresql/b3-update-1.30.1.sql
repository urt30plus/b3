CREATE TABLE IF NOT EXISTS plugin_hof (
  plugin_name VARCHAR(50) NOT NULL,
  map_name VARCHAR(100) NOT NULL,
  player_id INTEGER NOT NULL,
  score INTEGER NOT NULL DEFAULT '0',
  CONSTRAINT pk_hof UNIQUE (plugin_name, map_name)
);
