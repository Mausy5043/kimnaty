# SQLite3 script
# create table for Mija LYWSD03MMC device readings

DROP TABLE IF EXISTS data;
DROP TABLE IF EXISTS rooms;

CREATE TABLE data (
  sample_time   datetime NOT NULL,
  sample_epoch  integer,
  room_id       integer,
  temperature   real,
  humidity      real,
  voltage       real
  );

CREATE INDEX idx_time ON data(sample_time);
CREATE INDEX idx_epoch ON data(sample_epoch);

CREATE TABLE rooms (
    room_id     text NOT NULL PRIMARY KEY,
    name        text
  );

# Groundfloor
INSERT INTO rooms VALUES('0.0', 'hal');
INSERT INTO rooms VALUES('0.1.0', 'woonkamer voor');
INSERT INTO rooms VALUES('0.1.1', 'woonkamer achter');
INSERT INTO rooms VALUES('0.2', 'keuken');
INSERT INTO rooms VALUES('0.5', 'schuur');
INSERT INTO rooms VALUES('0.6', 'kweektafel');
INSERT INTO rooms VALUES('0.7.0', 'kas');
INSERT INTO rooms VALUES('0.9.0', 'buiten voor');
INSERT INTO rooms VALUES('0.9.1', 'buiten achter');
# 1st floor
INSERT INTO rooms VALUES('1.0', 'overloop');
INSERT INTO rooms VALUES('1.1', 'slaapkamer 1');
INSERT INTO rooms VALUES('1.2', 'slaapkamer 2');
INSERT INTO rooms VALUES('1.3', 'slaapkamer 3');
INSERT INTO rooms VALUES('1.4', 'badkamer');
# 2nd floor
INSERT INTO rooms VALUES('2.0', 'zolder');
INSERT INTO rooms VALUES('2.1', 'slaapkamer 4');


