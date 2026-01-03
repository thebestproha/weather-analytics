import React,{useEffect,useState}from"react";
import axios from"axios";
import{LineChart,Line,XAxis,YAxis,Tooltip,ResponsiveContainer}from"recharts";

const API="http://127.0.0.1:8000";

const cities=[
  "Chennai","Delhi","Mumbai","Bengaluru","Hyderabad",
  "Kolkata","Pune","Ahmedabad","Jaipur","Kochi","Trivandrum"
];

export default function App(){
  const[city,setCity]=useState("Chennai");
  const[current,setCurrent]=useState(null);
  const[hourly,setHourly]=useState([]);
  const[daily,setDaily]=useState([]);

  useEffect(()=>{
    axios.get(`${API}/weather/current/${city}`).then(r=>setCurrent(r.data));
    axios.get(`${API}/weather/predict/24h/${city}`).then(r=>{
      setHourly(r.data.temps.map((t,i)=>({h:i,temp:t})));
    });
    axios.get(`${API}/weather/predict/7d/${city}`).then(r=>{
      setDaily(r.data.temps.map((t,i)=>({d:i+1,temp:t})));
    });
  },[city]);

  return(
    <div style={{padding:20,fontFamily:"Arial"}}>
      <h2>🌤 Weather Analytics</h2>

      <select value={city}onChange={e=>setCity(e.target.value)}>
        {cities.map(c=><option key={c}>{c}</option>)}
      </select>

      {current&&(
        <h3>Current: {current.temperature} °C</h3>
      )}

      <h3>Next 24 Hours</h3>
      <ResponsiveContainer width="100%"height={250}>
        <LineChart data={hourly}>
          <XAxis dataKey="h"/>
          <YAxis/>
          <Tooltip/>
          <Line dataKey="temp"stroke="#ff7300"/>
        </LineChart>
      </ResponsiveContainer>

      <h3>Next 7 Days</h3>
      <ResponsiveContainer width="100%"height={250}>
        <LineChart data={daily}>
          <XAxis dataKey="d"/>
          <YAxis/>
          <Tooltip/>
          <Line dataKey="temp"stroke="#387908"/>
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
