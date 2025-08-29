# Private Placement Screener

**Author:** Robert Torres  
**Description:**  
A comprehensive Python-based private placement screener that fetches deal data, analyzes metrics, ranks and scores opportunities, and visualizes insights. Designed for integration with Bloomberg API or using mock data for testing and rapid prototyping. Ideal for data engineers, analysts, and investment professionals looking to identify the most promising private placement opportunities efficiently.

---

## Features

- Fetches data from **Bloomberg API** (or uses mock data if Bloomberg is unavailable)  
- Scores private placements based on **Yield, Market Cap, and Volume**  
- Ranks deals to highlight the most promising opportunities  
- Produces **interactive Plotly scatter plots** for visual analysis  
- Exports results to **CSV** for reporting and further analysis  
- Single Python file for **easy upload and deployment**  

---

## Installation

Ensure Python 3.10+ is installed. Clone the repository and install dependencies:

```bash
git clone <your-repo-url>
cd private_placement_screener
pip install pandas numpy matplotlib plotly blpapi
