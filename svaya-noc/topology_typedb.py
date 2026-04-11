from typedb.driver import TypeDB, SessionType, TransactionType

SCHEMA_QUERY = """
define
    name sub attribute, value string;
    status sub attribute, value string;

    # Entities
    network-element sub entity, abstract,
        owns name,
        owns status;
        
    router sub network-element,
        plays connection:upstream;
        
    cell sub network-element,
        plays connection:downstream;

    # Relations
    connection sub relation,
        relates upstream,
        relates downstream;

    # Logical Inference Rule (The "RDFox" Advantage)
    rule cell-isolation:
    when {
        $r isa router, has status "offline";
        $c isa cell;
        (upstream: $r, downstream: $c) isa connection;
    } then {
        $c has status "isolated";
    };
"""

DATA_QUERY = """
insert
    $r isa router, has name "CSR-Bangalore-Core-01", has status "online";
    $c isa cell, has name "Bangalore_Sector_105", has status "online";
    (upstream: $r, downstream: $c) isa connection;
"""

def setup_typedb():
    print("=== SVAYA TYPEDB KNOWLEDGE GRAPH SETUP ===")
    # Connect to local TypeDB server
    with TypeDB.core_driver("127.0.0.1:1729") as driver:
        # Create database if it doesn't exist
        if driver.databases.contains("svaya_telecom"):
            print("Database 'svaya_telecom' already exists. Recreating...")
            driver.databases.get("svaya_telecom").delete()
        
        driver.databases.create("svaya_telecom")
        print("Created database: svaya_telecom")

        # Open a schema session to define the ontology and rules
        with driver.session("svaya_telecom", SessionType.SCHEMA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                print("Defining Telecom Ontology and Inference Rules...")
                tx.query.define(SCHEMA_QUERY)
                tx.commit()

        # Open a data session to insert our POC topology
        with driver.session("svaya_telecom", SessionType.DATA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                print("Inserting Bangalore_Sector_105 and Core Router topology...")
                tx.query.insert(DATA_QUERY)
                tx.commit()
                
        print("TypeDB Setup Complete! You can now visualize this in TypeDB Studio.")

if __name__ == "__main__":
    try:
        setup_typedb()
    except Exception as e:
        print(f"Error connecting to TypeDB: {e}")
        print("Make sure TypeDB Core is running on port 1729!")
