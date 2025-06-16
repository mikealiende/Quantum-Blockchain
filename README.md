# Quantum-Blockchain

Master’s Thesis Project: Simulation of classical Bitcoin and a quantum Proof-of-Work (QBitCoin) based on QAOA and Max-Cut.

## Overview

This repository contains the code developed for the Master’s thesis “Design and simulation of a quantum cryptocurrency: Max-Cut as quantum Proof-of-Work”. It includes:

- Classical Bitcoin simulations (nonce search, 51% attack modeling).  
- Concurrent (multi-threaded) network simulations for classical mining.  
- QAOA implementations to solve Max-Cut on a quantum simulator.  
- Integration of QAOA into a prototype quantum Proof-of-Work (“QBitCoin”).  
- Attack scenarios, performance analysis, and comparisons between classical and quantum PoW.  
- Scripts and modules organized by stage or functionality:
  - `Simple_Simulation/`
  - `Threads_Simulation/`
  - `Quantum_simulation/`
  - `QAOA/`
  - `Attack_Simulation/`
  - etc.

Adjust details in sections like Dependencies and Usage to match the exact scripts and libraries used.

## Repository Structure

```text
Quantum-Blockchain/
├── Simple_Simulation/         # Basic classical Bitcoin simulation
│   ├── simulate_bitcoin.py
│   └── ...
├── Threads_Simulation/        # Multi-threaded network simulation
│   ├── run_threads_simulation.py
│   └── ...
├── Attack_Simulation/         # 51% attack modeling scripts
│   ├── attack_simulation.py
│   └── ...
├── QAOA/                      # QAOA implementation for Max-Cut
│   ├── run_qaoa.py
│   ├── qaoa_utils.py
│   └── ...
├── Quantum_simulation/        # QBitCoin simulation integrating quantum PoW
│   ├── simulate_qbitcoin.py
│   └── ...
├── graphs/                    # (Optional) sample graph files for Max-Cut
│   └── sample_graph.json
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── .gitignore
