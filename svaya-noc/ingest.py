import chromadb

def main():
    client = chromadb.PersistentClient(path="./chroma_db")
    try:
        client.delete_collection("telecom_sops")
    except Exception:
        pass
    collection = client.get_or_create_collection(name="telecom_sops")

    docs = [
        "SOP-Topology-001: Ericsson eNodeBs (ENB-101 through ENB-110) are daisy-chained and backhauled via the Cisco ASR-9000 Aggregation Router (Hostname: CSR-Central-1) on interface Gi0/0/1.",
        "SOP-CrossVendor-002: If an alarm storm occurs where multiple Ericsson eNodeBs report 'S1 Link Down' simultaneously, DO NOT dispatch field techs to the cell sites. Check the upstream Cisco backhaul router for physical interface drops or BGP routing failures.",
        "SOP-Ericsson-5G-001: For isolated 'X2 Link Failure' alarms, verify the physical fiber connection between eNodeB and gNodeB."
    ]

    for i, doc in enumerate(docs):
        collection.add(
            documents=[doc],
            metadatas=[{"source": f"Manual_{i}"}],
            ids=[f"id_{i}"]
        )
    print("Ingested Cross-Vendor SOPs and Topology!")

if __name__ == "__main__":
    main()
