import {useEffect,useState} from "react"
import axios from "axios"
import {LineChart,Line,XAxis,YAxis,Tooltip,CartesianGrid} from "recharts"

const API="http://127.0.0.1:8000"

function Card({title,value}){
  return(
    <div style={{
      padding:"16px",
      borderRadius:"12px",
      background:"#111",
      color:"#fff",
      minWidth:"180px"
    }}>
      <div style={{opacity:0.7,fontSize:"14px"}}>{title}</div>
      <div style={{fontSize:"28px",fontWeight:"bold"}}>{value}</div>
    </div>
  )
}

export default function App(){
  const[hourly,setHourly]=useState([])
  const[current,setCurrent]=useState(null)

  useEffect(()=>{
    axios.get(`${API}/weather/current/Chennai`).then(r=>setCurrent(r.data))
    axios.get(`${API}/weather/hourly/Chennai`).then(r=>setHourly(r.data))
  },[])

  return(
    <div style={{padding:"24px",fontFamily:"system-ui"}}>
      <h1>🌤 Weather Analytics – Chennai</h1>

      {current && (
        <div style={{display:"flex",gap:"16px",margin:"24px 0"}}>
          <Card title="Temperature (°C)" value={current.temperature}/>
          <Card title="Humidity (%)" value={current.humidity}/>
          <Card title="Pressure (hPa)" value={current.pressure}/>
          <Card title="Wind (m/s)" value={current.wind_speed}/>
        </div>
      )}

      <h2>Hourly Temperature</h2>
      <LineChart width={1000} height={420} data={hourly}>
        <CartesianGrid strokeDasharray="3 3"/>
        <XAxis dataKey="recorded_at"/>
        <YAxis/>
        <Tooltip/>
        <Line dataKey="temperature" stroke="#6366f1" dot={false}/>
      </LineChart>
    </div>
  )
}
