CREATE TABLE IF NOT EXISTS `plugin_hof` (
  `plugin_name` varchar(50) NOT NULL,
  `map_name` varchar(100) NOT NULL,
  `player_id` int(11) unsigned NOT NULL,
  `score` smallint(6) unsigned NOT NULL default '0',
  CONSTRAINT PK_HOF PRIMARY KEY (`plugin_name`, `map_name`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
