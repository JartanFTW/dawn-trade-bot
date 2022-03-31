PRAGMA user_version = 1;

CREATE TABLE cookie (
    roblosecurity text(764),
    user int(16),
    region text(2),
    birth_proxy text(16),
    created DATE DEFAULT (datetime('now', 'unixepoch')),
    flagged int(1) DEFAULT 0,

    PRIMARY KEY (roblosecurity),
    FOREIGN KEY (user) REFERENCES roblox_user (id)
    -- ON UPDATE CASCADE    dev: only here so I don't have to google how to do this later, ignore it
);

CREATE TABLE collectable (
    id int(16),
    roli_value int(8) DEFAULT NULL, -- other valuation methods can be added later
    rap int(8),
    updated DATE DEFAULT (datetime('now', 'unixepoch')),
    3d_rap int(8) DEFAULT NULL,
    7d_rap int(8) DEFAULT NULL,
    14d_rap int(8) DEFAULT NULL,
    30d_rap int(8) DEFAULT NULL,
    90d_rap int(8) DEFAULT NULL,
    180d_rap int(8) DEFAULT NULL,
    date_created DATE NOT NULL,

    -- any extra data we may need 

    PRIMARY KEY (id)
    FOREIGN KEY (id) REFERENCES trade (id)
);

CREATE TABLE roblox_user (
    id int(16),
    name int(16),
    accepted int(6) DEFAULT 0,
    sent int (6) DEFAULT 0,
    recieved int(6) DEFAULT 0,
    last_scanned DATE DEFAULT NULL,
    last_sent DATE DEFAULT NULL,

    -- any extra data that may be needed

    PRIMARY KEY (id)
);

CREATE TABLE trade (
    gitem1 int(16) NOT NULL,
    gitem2 int(16) DEFAULT NULL,
    gitem3 int(16) DEFAULT NULL,
    gitem4 int(16) DEFAULT NULL,
    titem1 int(16) NOT NULL,
    titem2 int(16) DEFAULT NULL,
    titem3 int(16) DEFAULT NULL,
    titem4 int(16) DEFAULT NULL,

    -- add some scoring details

    PRIMARY KEY (gitem1, gitem2, gitem3, gitem4)
);

CREATE TABLE collectable_ownership (
    userassetid int(16),
    collectable_id int(16),
    user_id int(16),
    updated DATE DEFAULT (datetime('now', 'unixepoch')),

    -- other details about the item as needed

    PRIMARY KEY (userassetsid),
    FOREIGN KEY (collectable_id) REFERENCES collectable(id),
    FOREIGN KEY (user_id) REFERENCES roblox_user(id)
);