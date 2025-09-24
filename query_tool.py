import sqlite3
import pandas as pd

def query_database():
    """
    A simple command-line tool to query the clinic_data.db SQLite database.
    """
    db_file = "clinic_data.db"
    
    try:
        con = sqlite3.connect(db_file)
        print(f"Successfully connected to {db_file}")

        while True:
            query = input("\nEnter your SQL query (or type 'exit' to quit): \n> ")
            if query.lower() == 'exit':
                break
            
            try:
                # Use pandas to execute the query and display the results in a clean table
                df = pd.read_sql_query(query, con)
                if df.empty:
                    print("Query executed successfully, but it returned no results.")
                else:
                    print(df.to_string())
            except Exception as e:
                print(f"An error occurred while executing the query: {e}")

    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
    finally:
        if con:
            con.close()
            print("\nDatabase connection closed.")

if __name__ == '__main__':
    query_database() 