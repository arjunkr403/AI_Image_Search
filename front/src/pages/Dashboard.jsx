import React, { useState, useEffect } from "react";
import RecentActivity from "../components/RecentActivity";
import StatsCard from "../components/StatsCard";
import SystemHealth from "../components/SystemHealth";
import { getDashboardStats } from "../services/api";

export default function Dashboard() {
  const [stats, setStats] = useState({
    total_images: 0,
    total_searches: 0,
    recent_activity: [],
  });

  useEffect(() => {
    async function fetchStats() {
      try {
        const data = await getDashboardStats();
        setStats(data);
      } catch (error) {
        console.error("Failed to load dashboard stats", error);
      }
    }
    fetchStats();
  }, []);

  return (
    <div className="space-y-6">
      {/* Statistics */}
     <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatsCard
          label="Total Searches"
          value={stats.total_searches.toLocaleString()}
          trend="--"
          trendType="neutral"
        />
        <StatsCard
          label="Total Images"
          value={stats.total_images.toLocaleString()}
          trend="+New"
          trendType="up"
        />
        <StatsCard
          label="Indexed Images"
          value="Dynamic"
          trend="Rebuilt on restart"
          trendType="neutral"
        />
      </section>


      {/* System Health and Recent Activity */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* system health */}
        <SystemHealth />

        {/* -------- Recent Activity -------- */}
        <RecentActivity data={stats.recent_activity} />
      </section>
    </div>
  );
}
