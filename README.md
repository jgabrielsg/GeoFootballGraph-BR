# GeoFootGraph-BR

**Author:** João Gabriel Machado  
**Institution:** Getulio Vargas Foundation (FGV) – School of Applied Mathematics (EMAp)  
**Course:** B.Sc. in Data Science and Artificial Intelligence  
**Year:** 2026

-----

## Project Overview

**GeoFootGraph-BR** is a technical framework designed to address the "Continental Paradox" of Brazilian football. Brazil's immense territory creates significant logistical and financial barriers for smaller clubs, often leading to insolvency or physiological exhaustion of athletes due to excessive travel. The current structure of competitions organized by the [CBF](https://www.cbf.com.br/) does not ensure a full-season calendar for clubs outside [Série A](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-a), [Série B](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b), and [Série C](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-c), effectively limiting consistent activity to just 60 teams and undermining the financial stability, fan engagement, and long-term viability of the remaining clubs. 

This project utilizes **Graph Theory**, **Geoprocessing**, and **Optimization Algorithms** to restructure the Brazilian league pyramid. By representing clubs as nodes (vertices) and transport routes/distances as edges (arcs), we aim to propose new tournament formats that minimize total displacement while maintaining competitive integrity and regional representation.

-----

## Data Strategy & Sources

Unlike initial iterations based on static government records, this version utilizes a custom-built, multi-source data engine to ensure accuracy and real-time relevance.

### 1\. Web Scraping (State & Regional Data)

Due to the lack of structured public datasets for lower-tier competitions, we developed custom Selenium-based scrapers (available in src/01_scraping) to extract data from [Ogol](https://www.ogol.com.br/), a well-maintained platform that compiles professional match data across all 27 state football federations in Brazil, including national competitions in recent years. We focused on matches played between 2020 and 2025, covering six full seasons of competitive football.

  - **Scope:** State Championships (Estaduais), State Federation Cups, and Regional Cups (such as Copa Verde and Copa do Nordeste);
  - **Process:** Automated extraction of match dates, scores, and club participation across first divisions of each state championship, as well as lower tiers (e.g., the fifth division in São Paulo and the third division in Goiás).

### 2\. External Contributions (National Data)

Data for national-level competitions was integrated from a high-quality repository, available below:

  - **Competitions:** Serie A, B, C, D, and Copa do Brasil.
  - **Sources:** - [BrazilianFootball/Data](https://github.com/BrazilianFootball/Data)
      - [IgorMichels](https://github.com/IgorMichels)
      - [MaxBiostat (FGV/EMAp)](https://github.com/maxbiostat)

### 3\. Geodata & Mapping

To transform club names into spatial coordinates, we utilized:

  - **Wikidata API:** Automated retrieval of stadium locations and headquarters coordinates.
  - **Manual Refinement:** Cleaning and correcting geodata for semi-professional and amateur clubs missing from global databases.
  - **Geodata Storage:** `data/01_raw/all_clubs_wikidata_geodata.csv`.

-----

## Project Structure

The repository is organized following a standard data science pipeline to ensure reproducibility:

```text
.
├── archive/              # Legacy scripts and experimental data
│   ├── data/             # Deprecated datasets
│   └── python/           # Old implementations
│
├── data/                 # Data Pipeline
│   ├── 01_raw/           # Original immutable data (JSONs, Scraped CSVs)
│   ├── 02_processed/     # Cleaned data, normalized names, merged tables
│   ├── 03_final/         # Finalized Graph structures and features
│   └── 04_results/       # CSVs/Tables with metrics (Centrality, Clusters)
│
├── links/                # Metadata and URL maps for the scraping engine
│
├── outputs/              # Project Deliverables
│   ├── maps/             # Folium/Geopandas spatial visualizations
│   ├── plots/            # Distribution and statistical charts
│   └── reports/          # Technical documentation and summaries
│
├── src/                  # Source Code
│   ├── 01_scraping/      # Selenium engines for data acquisition
│   ├── 02_preprocessing/ # Cleaning and geodata merging logic
│   ├── 03_analysis/      # General statistics and exploratory data analysis
│   ├── 04_page_rank/     # Ranking clubs by network influence
│   ├── 05_clustering/    # Community detection for regional league optimization
│   └── 06_visualizations/# Scripts for generating maps and graph plots
│
└── README.md
```

-----

## ⚙️ Methodology & Business Logic

The project's core logic is divided into three analytical pillars:

1.  **Topological Analysis:** Using **PageRank** and **Betweenness Centrality** to identify "Hub Clubs" and "Bridge Clubs" that define the connectivity of the Brazilian football ecosystem.
2.  **Geospatial Optimization:** Calculating the "Travel Burden" per league. We use the Haversine formula and REGIC 2018 (IBGE) connectivity matrices to simulate real-world logistics.
3.  **Community Detection:** Applying the **Louvain Method** or **K-Means** on graph embeddings to suggest regionalized clusters. This allows for a deeper pyramid where clubs only travel long distances when financially viable (e.g., National Stages).

-----

## 🛠 Tech Stack

  - **Language:** Python 3.10+
  - **Data Manipulation:** `pandas`, `numpy`, `json`
  - **Automation:** `undetected-chromedriver`, `selenium`
  - **Graph Theory:** `networkx`, `python-louvain`
  - **Geospatial:** `geopy`, `geopandas`, `folium`
  - **Visualization:** `matplotlib`, `seaborn`

-----

## 📄 License

This project is part of an undergraduate thesis at FGV. All code is provided under the MIT License. The data provided in `data/01_raw` belongs to the respective sources cited in the "Data Strategy" section.
