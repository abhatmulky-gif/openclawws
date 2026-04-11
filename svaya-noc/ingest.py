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
        "SOP-Ericsson-5G-001: For isolated 'X2 Link Failure' alarms, verify the physical fiber connection between eNodeB and gNodeB.",
        "SOP-Proactive-SON-Surge-01: If aggregated UE metrics show TTFB > 200ms and Video Stall Ratio > 5% while Cell PRB Utilization is > 85%, a sudden traffic surge is occurring. Action 1: Check neighboring cell capacity. Action 2: If neighbors have capacity, decrease 'a3Offset' by 2dB and increase 'qRxLevMin' by 2dB to force edge UEs to hand over. Action 3: If neighbors are full, enable CAC by adjusting 'dlPrbCongestionThreshold' to prioritize VoNR and active streaming."
    ]

    for i, doc in enumerate(docs):
        collection.add(
            documents=[doc],
            metadatas=[{"source": f"Manual_{i}"}],
            ids=[f"id_{i}"]
        )
    print("Ingested Cross-Vendor SOPs, Topology, and SON Surge Policies!")

if __name__ == "__main__":
    main()