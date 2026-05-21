// =============================================================================
// src/hooks/useWeather.ts — Fetch live weather based on user geolocation
// =============================================================================

import { useState, useEffect } from "react";
import { CloudRain, Sun, CloudSnow, CloudSun, Cloud, type LucideIcon } from "lucide-react";

export type DailyForecast = {
  dayKey: string;
  icon: LucideIcon;
  hi: number;
  lo: number;
};

export type WeatherData = {
  forecast: DailyForecast[];
  isRaining: boolean;
};

// Map WMO Weather code to Lucide Icon
function getWeatherIcon(code: number): LucideIcon {
  // 0: Clear sky
  if (code === 0) return Sun;
  // 1, 2, 3: Mainly clear, partly cloudy, and overcast
  if (code === 1 || code === 2) return CloudSun;
  if (code === 3) return Cloud;
  // 45, 48: Fog
  if (code === 45 || code === 48) return Cloud;
  // 51, 53, 55: Drizzle
  // 61, 63, 65: Rain
  // 80, 81, 82: Rain showers
  if ((code >= 51 && code <= 65) || (code >= 80 && code <= 82)) return CloudRain;
  // 71, 73, 75, 77: Snow fall
  // 85, 86: Snow showers
  if ((code >= 71 && code <= 77) || (code >= 85 && code <= 86)) return CloudSnow;
  // 95, 96, 99: Thunderstorm
  if (code >= 95) return CloudRain;
  return Sun;
}

const DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

export function useWeather() {
  const [data, setData] = useState<WeatherData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [permissionDenied, setPermissionDenied] = useState(false);

  useEffect(() => {
    // Only fetch once
    if (data || loading || error || permissionDenied) return;

    if (!("geolocation" in navigator)) {
      setError("Geolocation not supported");
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const lat = position.coords.latitude;
          const lon = position.coords.longitude;
          const res = await fetch(
            `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=5`
          );
          if (!res.ok) throw new Error("Weather API failed");
          
          const json = await res.json();
          const daily = json.daily;
          
          const forecast: DailyForecast[] = [];
          let isRaining = false;

          for (let i = 0; i < 5; i++) {
            const date = new Date(daily.time[i]);
            const code = daily.weathercode[i];
            const hi = Math.round(daily.temperature_2m_max[i]);
            const lo = Math.round(daily.temperature_2m_min[i]);
            const icon = getWeatherIcon(code);
            
            // Check if it's raining in the next 5 days
            if ((code >= 51 && code <= 65) || (code >= 80 && code <= 82) || code >= 95) {
              isRaining = true;
            }

            forecast.push({
              dayKey: DAYS[date.getDay()],
              icon,
              hi,
              lo,
            });
          }

          setData({ forecast, isRaining });
          setLoading(false);
        } catch (err: any) {
          setError(err.message);
          setLoading(false);
        }
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          setPermissionDenied(true);
        } else {
          setError(err.message);
        }
        setLoading(false);
      }
    );
  }, [data, loading, error, permissionDenied]);

  return { data, loading, error, permissionDenied };
}
