const historyData = [
  { id: 1, destination: "Minsk, Belarus", date: "Jul 12, 2026", type: "Solo" },
  { id: 2, destination: "Warsaw, Poland", date: "Jun 28, 2026", type: "Group" },
];

export default function HistoryPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold mb-6">Past Journeys</h2>
      
      {historyData.map((trip) => (
        <div key={trip.id} className="bg-[#1a1d24] border border-white/5 p-5 rounded-3xl flex justify-between items-center">
          <div>
            <h3 className="font-semibold">{trip.destination}</h3>
            <p className="text-xs text-gray-500">{trip.date}</p>
          </div>
          <span className="px-3 py-1 bg-white/5 rounded-full text-[10px] uppercase tracking-wider text-gray-400">
            {trip.type}
          </span>
        </div>
      ))}
    </div>
  );
}