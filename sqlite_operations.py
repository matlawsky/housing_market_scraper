import sqlite3


def setup_database():
    conn = sqlite3.connect("offers.db")
    cursor = conn.cursor()
    # CREATE FUNCTION TRUE() RETURNS INTEGER BEGIN RETURN 1; END;
    # CREATE FUNCTION FALSE() RETURNS INTEGER BEGIN RETURN 0; END;
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER UNIQUE PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL DEFAULT ('Unknown'),
            website TEXT NOT NULL,
            offer_id TEXT DEFAULT ('Unknown'),
            price TEXT DEFAULT ('Unknown'),
            offer_title TEXT DEFAULT ('Unknown'),
            location TEXT DEFAULT ('Unknown'),
            active TEXT DEFAULT ('Unknown'))
        """
    )
    conn.commit()
    conn.close()


def check_activate_offer(url, new_content):
    with sqlite3.connect("offers.db") as conn:
        cursor = conn.cursor()

        # Check if the offer exists
        cursor.execute("SELECT * FROM offers WHERE url = ?", (url,))
        offer = cursor.fetchone()

        if offer:
            # Update the offer if it exists
            cursor.execute(
                "UPDATE offers SET active = ? WHERE url = ?", (new_content, url)
            )
            conn.commit()
            print("Offer updated successfully.")
        else:
            print("Offer not found, no update performed.")


def get_detail_of_url(url):
    with sqlite3.connect("offers.db") as conn:
        cursor = conn.cursor()

        # Check if the offer exists
        cursor.execute("SELECT * FROM offers WHERE url = ?", (url,))
        offer = cursor.fetchone()

        if offer:
            # Update the offer if it exists
            cursor.execute("SELECT offers WHERE url = ?", (url))
            conn.commit()
            print("Offer updated successfully.")
        else:
            print("Offer not found, no update performed.")


def get_bool(inp: int):
    if inp == 0:
        return False
    else:
        return True


def put_bool(inp: bool):
    if inp == True:
        return 1
    else:
        return 0


def save_offer_to_db(data: dict):
    def check_value_present(value, column, default):
        """
        If value is present return it and if not return default
        """
        try:
            return value[column]
        except:
            return default

    conn = sqlite3.connect("offers.db")
    cursor = conn.cursor()
    # print(data.items())
    cursor.execute("BEGIN TRANSACTION")
    for key, value in data.items():

        # Query to find if the URL already exists and its active status
        cursor.execute("SELECT url, active FROM offers WHERE url = ?", (key,))
        result = cursor.fetchone()

        if result is not None:
            # Update existing entry if the active status has changed
            if result[-1] == "Unknown":
                cursor.execute(
                    "UPDATE offers SET active = ? WHERE url = ?",
                    (check_value_present(value, "is_active", 1), key),
                )
                print(f"Updated URL {key} with new active status {value['is_active']}")
        else:
            # Insert a new entry since the URL does not exist
            # keys = value.values()

            # entry = f"INSERT INTO offers (url, category, website, offer_id, price, offer_title, location, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            cursor.execute(
                "INSERT INTO offers (url, category, website, offer_id, price, offer_title, location, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    (
                        key,
                        str(value["size_category"]),
                        str(key.split(".pl")[0].split("www.")[1]),
                        check_value_present(value, "offer_id", "Unknown"),
                        check_value_present(value, "price", "Unknown"),
                        check_value_present(value, "offer_title", "Unknown"),
                        check_value_present(value, "location", "Unknown"),
                        put_bool(check_value_present(value, "is_active", True)),
                    )
                ),
            )
            print(f"Inserted new offer with URL {key}")

        conn.commit()
    conn.close()


def multiproc_save_to_db(data: dict):
    def check_value_present(value, column, default):
        """
        If value is present return it and if not return default
        """
        try:
            return value[column]
        except:
            return default

    conn = sqlite3.connect("offers.db")
    cursor = conn.cursor()
    # print(data.items())
    cursor.execute("BEGIN TRANSACTION")
    for key, value in data.items():
        # Check if a record with given url exists
        # and if it does check if the acitve is Unkown
        # if it is Unknown update all values
        # if active is Yes or No we can update only active

        # Query to find if the URL already exists and its active status
        entry = f"""
            INSERT INTO offers (url, category, website, offer_id, price, offer_title, location, active) ({str('key,') + str([str(' ' + str(i)) + ',' for i in value.keys() ])})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (url) DO
            UPDATE
            SET
                url = excluded.name
                category = excluded.category
                website = excluded.website
                offer_id = excluded.offer_id
                price = excluded.price
                offer_title = excluded.offer_title
                location = excluded.location
                active = 
            WHERE
                offers.active = 'Unknown' 
            """

        cursor.execute(
            """
            INSERT INTO offers (url, category, website, offer_id, price, offer_title, location, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (url) DO
            UPDATE
            SET
                url = excluded.name
                category = excluded.category
                website = excluded.website
                offer_id = excluded.offer_id
                price = excluded.price
                offer_title = excluded.offer_title
                location = excluded.location
                active = excluded.active
            WHERE
                excluded.effective_date > contacts.effective_date
            """,
            (
                (
                    key,
                    str(value["size_category"]),
                    str(key.split(".pl")[0].split("www.")[1]),
                    check_value_present(value, "offer_id", "Unknown"),
                    check_value_present(value, "price", "Unknown"),
                    check_value_present(value, "offer_title", "Unknown"),
                    check_value_present(value, "location", "Unknown"),
                    put_bool(check_value_present(value, "is_active", True)),
                )
            ),
        )
        print(f"Inserted new offer with URL {key}")

        conn.commit()
    conn.close()


# setup_database()  # Call this at the start to ensure the database and table are ready.
