import {useEffect,useState} from "react"
import axios from "axios"
import {
  LineChart,Line,CartesianGrid,XAxis,YAxis,Tooltip,ResponsiveContainer
} from "recharts"

export default function App(){
  const[hourly,setHourly]=useState([])
  const[pred,setPred]=useState([])
  const[current,setCurrent]=useState(null)

  useEffect(()=>{
    axios.get("http://127.0.0.1:8000/weather/current/Chennai")
      .then(r=>setCurrent(r.data))

    axios.get("http://127.0.0.1:8000/weather/hourly/Chennai")
      .then(r=>setHourly(r.data.map((d,i)=>({x:i,temp:d.temperature}))))

    axios.get("http://127.0.0.1:8000/weather/predict/Chennai")
      .then(r=>setPred(r.data.map((d,i)=>({x:i,temp:d.predicted_temperature}))))
  },[])

  return(
    <div className="container">
      <div className="header">🌤 Weather Analytics — Chennai</div>

      <div className="cards">
        <div className="card">
          <span>Temperature</span>
          <strong>{current?current.temperature:"--"} °C</strong>
        </div>
        <div className="card">
          <span>Humidity</span>
          <strong>{current?current.humidity:"--"} %</strong>
        </div>
        <div className="card">
          <span>Pressure</span>
          <strong>{current?current.pressure:"--"} hPa</strong>
        </div>
      </div>

      <div className="section">
        <h3>Hourly Temperature (Observed)</h3>
        <div className="chartBox" style={{height:300}}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={hourly}>
              <CartesianGrid stroke="#333"/>
              <XAxis dataKey="x"/>
              <YAxis/>
              <Tooltip/>
              <Line type="monotone" dataKey="temp" stroke="#4ade80"/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="section">
        <h3>Next 24 Hours (Prediction)</h3>
        <div className="chartBox" style={{height:300}}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={pred}>
              <CartesianGrid stroke="#333"/>
              <XAxis dataKey="x"/>
              <YAxis/>
              <Tooltip/>
              <Line type="monotone" dataKey="temp" stroke="#60a5fa"/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
