# Agricultural Land Suitability Assessment Tool for Wheat and Barley

**Agricultural Land Suitability Tool --- Wheat & Barley**

This ArcGIS Pro tool is designed to assess agricultural land suitability
for wheat and barley using the FAO land evaluation framework, weighted
multi-criteria evaluation, and fuzzy logic.

> **Note:** This README documents the information provided in the
> original HTML user guide. It does not include the Python toolbox file
> `WheatBarleySuitability.pyt` itself.

## Table of Contents

-   [1. Installation and Setup](#1-installation-and-setup)
-   [2. Available Tools](#2-available-tools)
-   [3. Supported Analytical Methods](#3-supported-analytical-methods)
-   [4. Land Suitability Classes](#4-land-suitability-classes)
-   [5. Environmental Parameters and Default
    Weights](#5-environmental-parameters-and-default-weights)
-   [6. Workflow](#6-workflow)
-   [7. Data Requirements and Sources](#7-data-requirements-and-sources)
-   [8. Wheat and Barley Requirements
    Compared](#8-wheat-and-barley-requirements-compared)
-   [9. Frequently Asked Questions and
    Troubleshooting](#9-frequently-asked-questions-and-troubleshooting)

## 1. Installation and Setup

1.  **Copy the toolbox file:** Copy `WheatBarleySuitability.pyt` into
    your project folder or another suitable location on your computer.

2.  **Add the toolbox to ArcGIS Pro:**

    -   Open the **Catalog** pane.
    -   Navigate to **Toolboxes**.
    -   Right-click and select **Add Toolbox**.
    -   Browse to and select the `.pyt` file.
    -   Alternatively, drag the file directly from Windows File Explorer
        into the ArcGIS Pro Catalog pane.

3.  **Check the license:** Make sure that an **ArcGIS Spatial Analyst**
    license is available. According to the guide, the tool checks
    license availability automatically when opened.

    Menu path shown in the guide:
    `Project → Licensing → Configure → Spatial Analyst`

4.  **Open the toolbox:** After adding it, you should see the three
    tools described below.

## 2. Available Tools

  Tool     Function
  -------- ----------------------------------------------------------
  Tool 1   Main land suitability assessment for wheat and/or barley
  Tool 2   Weight sensitivity analysis
  Tool 3   Statistical area report

## 3. Supported Analytical Methods

### 3.1 FAO Limiting Factor Method

This method follows the principle that **the weakest link determines the
overall result**. The lowest suitability value among all parameters
determines the final result.

-   More conservative.
-   Easy to interpret.
-   The guide associates it with the FAO methodology (1976).

### 3.2 Weighted Multi-Criteria Evaluation (MCE)

This method assigns a relative weight to each parameter according to its
importance. The final score is calculated as the weighted sum:

``` text
Score = Σ (Wi × Si) / Σ Wi
```

Where: - `Wi`: Weight assigned to the parameter. - `Si`: Suitability
score of the parameter.

The method is flexible, allows weight customization, and permits
compensation between criteria.

### 3.3 Fuzzy Logic

The guide uses a Gaussian membership function to represent gradual
transitions in suitability rather than sharp thresholds. Optimal values
receive a membership value of `1.0`, which gradually decreases as values
move away from the optimum.

``` text
μ(x) = exp(-0.5 × ((x - mid) / σ)²)
```

### 3.4 Combined Method

The combined method integrates weighted multi-criteria evaluation and
the limiting factor method using the following equation:

``` text
Final Score = (WCE × 0.70) + (LF × 0.30)
```

Where: - `WCE`: Weighted multi-criteria evaluation result (70%). - `LF`:
Limiting factor result (30%).

The guide recommends this method for research and planning projects
because it balances flexibility and conservatism and allows partial
compensation between criteria.

## 4. Land Suitability Classes

The guide presents five suitability classes:

  Class     Score Range Description                  Raster Value
  ------- ------------- -------------------------- --------------
  S1            80--100 Highly Suitable                         5
  S2             60--79 Moderately Suitable                     4
  S3             40--59 Marginally Suitable                     3
  N1             20--39 Currently Not Suitable                  2
  N2              0--19 Permanently Not Suitable                1

The raster values from 1 to 5 allow further analysis and map
visualization.

## 5. Environmental Parameters and Default Weights

The following values are the default values presented in the original
HTML guide. The S1 columns show the ranges for high suitability, while
the weight columns show the percentage assigned to each parameter.

  --------------------------------------------------------------------------------------------
  Parameter     Unit         Wheat S1            Barley S1       Wheat      Barley Source
                                                                Weight      Weight cited in
                                                                                   the guide
  ------------- --------- ----------- -------------------- ----------- ----------- -----------
  Temperature   °C             12--22               10--25         18%         16% FAO/IIASA

  Rainfall      mm/year      400--700             300--600         20%         18% FAO 1976

  Slope         \%               0--5                 0--6         12%         12% FAO/USDA

  Soil depth    cm              \>100                 \>80         10%         10% USDA SCS

  Soil pH       pH           6.0--7.5             6.0--8.0         10%         10% FAO 1985

  Salinity (EC) dS/m             0--4                 0--6         12%         12% FAO Irrig.
                                                                                   29

  Organic       \%               \>2%               \>1.5%          8%          8% Brady &
  matter                                                                           Weil

  Drainage      Class            Very                 Very         10%         10% USDA
                1--6        good/good   good/good/moderate                         

  Calcium       \%              0--15                0--20    Optional    Optional FAO 1990
  carbonate                                                                        
  (CaCO₃)                                                                          
  --------------------------------------------------------------------------------------------

Weights can be customized through the JSON field in the tool. Note that
the listed default weights for each crop sum to 100%, excluding optional
CaCO₃.

## 6. Workflow

1.  **Open Tool 1 --- Main Land Suitability Assessment.** Double-click
    the first tool in the toolbox.

2.  **Select the crop and analytical method:**

    -   Crop: wheat, barley, or both.
    -   Method: the guide recommends the combined method.

3.  **Provide the input raster datasets:** Add the available parameter
    rasters. The guide states that not all parameters are mandatory and
    mentions 2--3 available parameters as a minimum for this workflow.

    -   If a slope raster is unavailable, provide a Digital Elevation
        Model (DEM); the tool will calculate slope automatically.

4.  **Customize weights if required:** Modify the weights in the JSON
    field. The following example is provided in the guide:

    ``` json
    {
      "temp": 0.20,
      "rainfall": 0.25,
      "slope": 0.15,
      "soil_depth": 0.10,
      "ph": 0.10,
      "ec": 0.10,
      "organic_matter": 0.05,
      "drainage": 0.05
    }
    ```

    Make sure the sum of the weights equals `1.0` (100%). The guide
    states that weights are automatically normalized if their sum is not
    1.0.

5.  **Set the output folder and file name:** Select the output directory
    and specify the name of the resulting suitability raster (`.tif`).

    -   You can enable **Create Individual Parameter Classification
        Rasters** to save a separate classification raster for each
        parameter. This is useful for analysis and review.

6.  **Run the tool:** According to the guide, the outputs include:

    -   Final suitability raster with class values from 1 to 5.
    -   Individual parameter classification rasters, if the relevant
        option is enabled.
    -   Interactive HTML report.

7.  **Generate the statistical report:** Run Tool 3 on the resulting
    raster to calculate the area of each suitability class in multiple
    units: hectares, km², dunams, and acres.

## 7. Data Requirements and Sources

  -----------------------------------------------------------------------
  Dataset           Format            Suggested sources Notes
                                      in the guide      
  ----------------- ----------------- ----------------- -----------------
  Digital Elevation Raster            SRTM 30m, ASTER   Used to derive
  Model (DEM)                         30m, Copernicus   slope
                                      30m               automatically

  Temperature       Raster            WorldClim 2.1,    Annual mean or
                                      CHELSA, ERA5      growing-season
                                                        mean

  Rainfall          Raster            WorldClim 2.1,    Annual total in
                                      CHIRPS, GPM IMERG millimeters

  Soil properties   Raster / Vector   SoilGrids 250m,   Includes pH, OC,
                                      FAO World Soil    EC, depth, and
                                                        texture

  Drainage map      Raster            HWSD, local       Classes 1--6
                                      geological maps   according to USDA
  -----------------------------------------------------------------------

### Free Data Download Links

-   [WorldClim 2.1 --- Climate
    Data](https://worldclim.org/data/worldclim21.html)
-   [SoilGrids --- Soil Data](https://soilgrids.org)
-   [USGS EarthExplorer --- SRTM DEM](https://earthexplorer.usgs.gov)
-   [CHELSA --- Climate Data](https://chelsa-climate.org)
-   [CHIRPS --- Rainfall Data](https://www.chc.ucsb.edu/data/chirps)

### Preparing Data Before Running the Tool

All input rasters should:

-   Use the same coordinate reference system.
-   Have compatible cell sizes.
-   Be spatially aligned and, as far as possible, have compatible
    extents.

The guide recommends using **Project Raster** and **Resample** in ArcGIS
Pro when necessary.

## 8. Wheat and Barley Requirements Compared

  ----------------------------------------------------------------------------
  Parameter                 Wheat (S1)          Barley (S1) Main difference
                                                            stated in the
                                                            guide
  --------------- -------------------- -------------------- ------------------
  Rainfall                 400--700 mm          300--600 mm Barley is more
                                                            drought-tolerant

  Temperature                12--22 °C            10--25 °C Barley has a wider
                                                            range

  Salinity (EC)               \<4 dS/m             \<6 dS/m Barley is more
                                                            salt-tolerant

  pH                          6.0--7.5             6.0--8.0 Barley tolerates
                                                            higher alkalinity

  Soil depth                  \>100 cm              \>80 cm Wheat requires
                                                            greater soil depth

  Organic matter                  \>2%               \>1.5% Wheat has higher
                                                            nutrient
                                                            requirements
  ----------------------------------------------------------------------------

**Summary from the guide:** Barley is more flexible and tolerant of
harsh conditions, making it suitable for semi-arid areas and soils with
moderate salinity. Wheat requires better and more stable growing
conditions.

## 9. Frequently Asked Questions and Troubleshooting

### Can point data be used instead of raster datasets?

Yes. The guide recommends converting point data into a raster using
**IDW** or **Kriging** in ArcGIS Pro first.

### What if the input rasters use different units?

The guide states that the tool can work with different units, provided
that the input values match the units used for the minimum and maximum
thresholds defined in the tool.

### What is the minimum number of required parameters?

The guide states that one parameter is technically sufficient, but
recommends at least 4--5 parameters for reliable results. Its workflow
section also mentions that 2--3 available parameters can be used. These
statements distinguish the technical minimum from the recommendation for
improving assessment reliability.

### How can additional parameters be added in the future?

According to the guide, the `.pyt` file must be modified:

1.  Add the new parameter to the `CROP_REQUIREMENTS` dictionary.
2.  Create a corresponding input parameter in the `getParameterInfo()`
    function.

### How can the "Spatial Analyst license unavailable" error be resolved?

Check that the **Spatial Analyst** license is enabled in ArcGIS Pro:

`Project → Licensing → Configure`

## Important Notes

-   This README converts the original HTML guide into Markdown format
    (`README.md`) for convenient use in a GitHub repository or an ArcGIS
    Pro project folder.
-   The HTML guide does not contain the Python toolbox source file
    `WheatBarleySuitability.pyt`. It therefore does not, by itself,
    demonstrate that all described functions have been implemented or
    tested.
-   All parameter ranges, thresholds, weights, and methodological
    descriptions above are reproduced from the original guide. Their
    suitability for a particular study area and crop should be validated
    against appropriate local data and references before final results
    are adopted or published.

------------------------------------------------------------------------

**Agricultural Land Suitability Assessment Tool for Wheat and Barley \|
ArcGIS Pro Python Toolbox**

Methodological frameworks cited in the guide: FAO Land Evaluation
Framework (1976), IIASA, and USDA.

License statement in the guide: For academic and research use.
