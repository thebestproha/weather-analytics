import cdsapi

def download_city_month(city,lat,lon,year,month,mode,outfile):
    c=cdsapi.Client()

    variables={
        "instant":[
            "2m_temperature",
            "2m_dewpoint_temperature",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "surface_pressure"
        ],
        "accum":[
            "total_precipitation"
        ]
    }

    c.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type":"reanalysis",
            "variable":variables[mode],
            "year":str(year),
            "month":f"{month:02d}",
            "day":[f"{d:02d}" for d in range(1,32)],
            "time":[f"{h:02d}:00" for h in range(24)],
            "area":[lat+0.1,lon-0.1,lat-0.1,lon+0.1],
            "format":"netcdf"
        },
        str(outfile)
    )
