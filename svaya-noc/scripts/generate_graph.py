import networkx as nx
import matplotlib.pyplot as plt
import os

def create_topology_graph():
    # Initialize Directed Graph
    G = nx.DiGraph()
    
    # Define Nodes and properties
    router = "Cisco ASR-9000\n(CSR-Central-1)"
    e1 = "Ericsson eNodeB\n(ENB-101)"
    e2 = "Ericsson eNodeB\n(ENB-102)"
    e3 = "Ericsson eNodeB\n(ENB-103)"
    n1 = "Nokia AirScale\ngNodeB (Cell 1)"
    n2 = "Nokia AirScale\ngNodeB (Cell 2)"
    
    G.add_node(router, color='#87CEEB') # Light Blue
    G.add_node(e1, color='#98FB98')     # Pale Green
    G.add_node(e2, color='#98FB98')
    G.add_node(e3, color='#98FB98')
    G.add_node(n1, color='#FFB6C1')     # Light Pink for Nokia
    G.add_node(n2, color='#FFB6C1')
    
    # Define Edges (All connected directly to Cisco Router)
    G.add_edge(router, e1, label="Gi0/0/1")
    G.add_edge(router, e2, label="Gi0/0/2")
    G.add_edge(router, e3, label="Gi0/0/3")
    G.add_edge(router, n1, label="Gi0/0/4")
    G.add_edge(router, n2, label="Gi0/0/5")
    
    # Plotting setup
    plt.figure(figsize=(12, 8))
    
    # Custom Positions
    pos = {
        router: (0.5, 1.0),
        e1: (0.1, 0.5),
        e2: (0.3, 0.5),
        e3: (0.5, 0.5),
        n1: (0.7, 0.5),
        n2: (0.9, 0.5)
    }
    
    colors = [node[1]['color'] for node in G.nodes(data=True)]
    
    # Draw Nodes and Labels
    nx.draw(G, pos, with_labels=True, node_color=colors, node_size=6000, 
            font_size=9, font_weight="bold", arrows=True, arrowsize=20)
    
    # Draw Edge Labels
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', font_size=10)
    
    # Save image
    output_path = os.path.join(os.path.dirname(__file__), "svaya_topology_updated.png")
    plt.title("Svaya NOC - Updated Topology Map", size=16)
    plt.margins(0.2)
    plt.savefig(output_path, format="PNG", bbox_inches="tight")
    print(f"Graph successfully generated at: {output_path}")

if __name__ == "__main__":
    create_topology_graph()
