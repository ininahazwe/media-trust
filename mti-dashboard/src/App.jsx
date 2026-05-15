import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';

export default function MTIDashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  const [outletDetails, setOutletDetails] = useState({});
  const [selectedOutlet, setSelectedOutlet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_URL = 'http://localhost:8000';

  // Fetch dashboard data
  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_URL}/api/dashboard`);
        const data = await response.json();
        setDashboardData(data);

        // Fetch detailed responses for dimensions
        const responsesRes = await fetch(`${API_URL}/api/responses`);
        const responses = await responsesRes.json();

        // Group by outlet
        const byOutlet = {};
        responses.forEach(r => {
          if (!byOutlet[r.outlet_id]) {
            byOutlet[r.outlet_id] = [];
          }
          byOutlet[r.outlet_id].push(r);
        });

        setOutletDetails(byOutlet);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Error fetching data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
    const interval = setInterval(fetchDashboard, 30000); // Refresh every 30s

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-50">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading dashboard...</p>
          </div>
        </div>
    );
  }

  if (error) {
    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-50">
          <div className="text-center">
            <p className="text-red-600 font-semibold">Error: {error}</p>
            <p className="text-gray-600 text-sm mt-2">Make sure the API is running on {API_URL}</p>
          </div>
        </div>
    );
  }

  const mostTrustedOutlet = dashboardData?.top_outlets?.[0];
  const chartData = dashboardData?.top_outlets?.map((outlet, idx) => ({
    name: outlet.name,
    'MTI Score': outlet.score || 0,
  })) || [];

  // Calculate average dimensions
  const allResponses = Object.values(outletDetails).flat();
  const avgDimensions = allResponses.length > 0 ? {
    accuracy: Math.round(allResponses.reduce((sum, r) => sum + r.accuracy_score, 0) / allResponses.length),
    verification: Math.round(allResponses.reduce((sum, r) => sum + r.verification_score, 0) / allResponses.length),
    independence: Math.round(allResponses.reduce((sum, r) => sum + r.independence_score, 0) / allResponses.length),
    fair_balanced: Math.round(allResponses.reduce((sum, r) => sum + r.fair_balanced_score, 0) / allResponses.length),
    public_interest: Math.round(allResponses.reduce((sum, r) => sum + r.public_interest_score, 0) / allResponses.length),
    corrections: Math.round(allResponses.reduce((sum, r) => sum + r.corrections_score, 0) / allResponses.length),
  } : {};

  const dimensionsData = [
    { name: 'Accuracy', value: avgDimensions.accuracy || 0 },
    { name: 'Verification', value: avgDimensions.verification || 0 },
    { name: 'Independence', value: avgDimensions.independence || 0 },
    { name: 'Fair & Balanced', value: avgDimensions.fair_balanced || 0 },
    { name: 'Public Interest', value: avgDimensions.public_interest || 0 },
    { name: 'Corrections', value: avgDimensions.corrections || 0 },
  ];

  return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-6">
            <h1 className="text-3xl font-bold text-gray-900">Media Trust Index</h1>
            <p className="text-gray-600 text-sm mt-1">Ghana Survey Round 1 • {dashboardData?.total_responses || 0} responses</p>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-6 py-8">
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {/* Average MTI Score */}
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-600">
              <h3 className="text-gray-600 text-sm font-semibold uppercase tracking-wide mb-2">Average MTI Score</h3>
              <p className="text-4xl font-bold text-blue-600">{dashboardData?.average_mti?.toFixed(1) || 0}</p>
              <p className="text-green-600 text-xs mt-3">📈 Based on {dashboardData?.total_responses || 0} responses</p>
            </div>

            {/* Most Trusted Outlet */}
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-purple-600">
              <h3 className="text-gray-600 text-sm font-semibold uppercase tracking-wide mb-2">Most Trusted Outlet</h3>
              <p className="text-2xl font-bold text-purple-600">{mostTrustedOutlet?.name || 'N/A'}</p>
              <p className="text-gray-600 text-sm mt-2">MTI: <span className="font-semibold text-purple-600">{mostTrustedOutlet?.score?.toFixed(1) || 0}</span></p>
            </div>

            {/* Total Respondents */}
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-pink-600">
              <h3 className="text-gray-600 text-sm font-semibold uppercase tracking-wide mb-2">Respondents</h3>
              <p className="text-4xl font-bold text-pink-600">{dashboardData?.total_respondents || 0}</p>
              <p className="text-gray-600 text-xs mt-3">Unique survey respondents</p>
            </div>

            {/* Total Outlets */}
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-orange-600">
              <h3 className="text-gray-600 text-sm font-semibold uppercase tracking-wide mb-2">Media Outlets</h3>
              <p className="text-4xl font-bold text-orange-600">{dashboardData?.total_outlets || 0}</p>
              <p className="text-gray-600 text-xs mt-3">Total outlets surveyed</p>
            </div>
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Top Outlets Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">Top Media Outlets</h2>
              {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="MTI Score" fill="#6366f1" />
                    </BarChart>
                  </ResponsiveContainer>
              ) : (
                  <p className="text-gray-500 text-center py-8">No data available</p>
              )}
            </div>

            {/* Dimensions Radar */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">Trust Dimensions</h2>
              <p className="text-sm text-gray-600 mb-4">Average scores across all outlets</p>
              {dimensionsData.some(d => d.value > 0) ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <RadarChart data={dimensionsData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="name" />
                      <PolarRadiusAxis />
                      <Radar name="Score" dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.6} />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
              ) : (
                  <p className="text-gray-500 text-center py-8">No data available</p>
              )}
            </div>
          </div>

          {/* Dimensions Progress Bars */}
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-lg font-bold text-gray-900 mb-6">Trust Dimensions Breakdown</h2>
            <div className="space-y-6">
              {dimensionsData.map((dim) => (
                  <div key={dim.name}>
                    <div className="flex justify-between items-center mb-2">
                      <label className="text-sm font-semibold text-gray-900">{dim.name}</label>
                      <span className="text-sm font-bold text-indigo-600">{dim.value}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                          className="bg-indigo-600 h-3 rounded-full transition-all duration-300"
                          style={{ width: `${Math.min(dim.value, 100)}%` }}
                      ></div>
                    </div>
                  </div>
              ))}
            </div>
          </div>

          {/* Outlets Table */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">All Outlets</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Outlet Name</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">MTI Score</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Responses</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Average Trust</th>
                </tr>
                </thead>
                <tbody>
                {dashboardData?.top_outlets?.map((outlet, idx) => {
                  const responses = allResponses.filter(r => r.outlet_id === (idx + 1));
                  const avgTrust = responses.length > 0
                      ? Math.round(responses.reduce((sum, r) => sum + r.accuracy_score, 0) / responses.length)
                      : 0;

                  return (
                      <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4 text-sm text-gray-900">{outlet.name}</td>
                        <td className="py-3 px-4 text-sm">
                          <span className="font-bold text-indigo-600">{outlet.score?.toFixed(1) || 0}</span>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-600">{responses.length}</td>
                        <td className="py-3 px-4 text-sm">
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-gray-200 rounded h-2">
                              <div
                                  className="bg-indigo-600 h-2 rounded transition-all"
                                  style={{ width: `${avgTrust}%` }}
                              ></div>
                            </div>
                            <span className="text-xs text-gray-600">{avgTrust}%</span>
                          </div>
                        </td>
                      </tr>
                  );
                })}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>
  );
}