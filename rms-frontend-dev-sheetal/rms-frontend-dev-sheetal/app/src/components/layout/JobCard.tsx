import { MapPin, Briefcase } from "lucide-react";

interface JobCardProps {
  title: string;
  company: string;
  location: string;
  experience: string;
  status?: string;
}

export default function JobCard({
  title,
  company,
  location,
  experience,
  status = "Open",
}: JobCardProps) {
  return (
    <div className="border rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-gray-500">{company}</p>

      <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
        <span className="flex items-center gap-1">
          <MapPin size={14} /> {location}
        </span>
        <span className="flex items-center gap-1">
          <Briefcase size={14} /> {experience}
        </span>
      </div>

      <span
        className={`mt-3 inline-block px-3 py-1 text-xs rounded-full ${
          status === "Open"
            ? "bg-green-100 text-green-700"
            : status === "Closed"
            ? "bg-red-100 text-red-700"
            : "bg-yellow-100 text-yellow-700"
        }`}
      >
        {status}
      </span>
    </div>
  );
}
