# Project Overview: CityCam Metadata Forensic System
CityCam is a specialized backend forensic tool designed to transform raw surveillance logs into actionable intelligence. Unlike standard video storage systems, this engine focuses on Metadata Analysis, indexing specific vehicle attributes—such as color, type, and unique identifiers—to enable rapid search and movement reconstruction across an urban camera network.

Key Capabilities
Forensic Query Engine: Allows investigators to filter through millions of sightings using specific metadata traits (e.g., "Find all Red SUVs spotted between 9:00 AM and 11:00 AM").

Path Reconstruction (Stage 4): Automatically sequences isolated data points into a chronological "Breadcrumb Trail," visually mapping the trajectory of a subject through the city grid.

Relational Geo-Mapping: Uses SQL joins to link abstract camera IDs to physical real-world locations, providing human-readable context to digital logs.

Integrity Validation (Stage 5): Employs spatial-temporal logic to detect "impossible" sightings, flagging data inconsistencies or potential system tampering.

The Technical Stack
Language: Python 3.x

Database: MySQL / MariaDB (Relational Architecture)

Logic: Chronological sorting and Haversine-based distance validation.m
