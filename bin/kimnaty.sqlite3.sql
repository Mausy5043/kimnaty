# SQLite3 script


--TABLE data is used to store RH/T data from Mija LYWSD03MMC devices
DROP TABLE IF EXISTS data;

CREATE TABLE data (
    sample_time   datetime NOT NULL,
    sample_epoch  integer NOT NULL,
    sample_epoch  integer,
    room_id       integer,
    temperature   real,
    humidity      real,
    voltage       real
    );

CREATE INDEX idx_data_time ON data(sample_time);
CREATE INDEX idx_data_epoch ON data(sample_epoch);


-- TABLE rooms is used to link room_id with human-readable room names
DROP TABLE IF EXISTS rooms;

CREATE TABLE rooms (
    room_id     text NOT NULL PRIMARY KEY,
    name        text NOT NULL
  );
-- Prefill the table with roomnames
-- Groundfloor
INSERT INTO rooms VALUES('0.0', 'hal');
INSERT INTO rooms VALUES('0.1.0', 'woonkamer voor');
INSERT INTO rooms VALUES('0.1.1', 'woonkamer achter');
INSERT INTO rooms VALUES('0.2', 'keuken');
INSERT INTO rooms VALUES('0.5', 'schuur');
INSERT INTO rooms VALUES('0.6', 'kweektafel');
INSERT INTO rooms VALUES('0.7.0', 'kas');
INSERT INTO rooms VALUES('0.9.0', 'buiten voor');
INSERT INTO rooms VALUES('0.9.1', 'buiten achter');
-- 1st floor
INSERT INTO rooms VALUES('1.0', 'overloop');
INSERT INTO rooms VALUES('1.1', 'slaapkamer 1');
INSERT INTO rooms VALUES('1.2', 'slaapkamer 2');
INSERT INTO rooms VALUES('1.3', 'slaapkamer 3');
INSERT INTO rooms VALUES('1.4', 'badkamer');
-- 2nd floor
INSERT INTO rooms VALUES('2.0', 'zolder');
INSERT INTO rooms VALUES('2.1', 'slaapkamer 4');


-- TABLE aircon is used to store data from the DAIKIN airconditioners
DROP TABLE IF EXISTS aircon;

CREATE TABLE aircon (
    sample_time         datetime NOT NULL,
    sample_epoch        integer NOT NULL,
    room_id             integer,
    ac_power            integer,
    ac_mode             integer,
    temperature_ac      real,
    temperature_target  real,
    temperature_outside real,
    cmp_freq            integer
    );

CREATE INDEX idx_ac_time ON aircon(sample_time);
CREATE INDEX idx_ac_epoch ON aircon(sample_epoch);
