import clsx from "clsx";

interface Props {
  label: string;
  value: string;
  sub?: string;
  color?: "green" | "red" | "blue" | "gray";
  icon?: React.ReactNode;
}

const COLOR_MAP = {
  green: "text-green-600 bg-green-50",
  red: "text-red-600 bg-red-50",
  blue: "text-blue-600 bg-blue-50",
  gray: "text-gray-700 bg-gray-100",
};

export default function StatTile({ label, value, sub, color = "gray", icon }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-2">
        {icon && (
          <span className={clsx("p-1.5 rounded-lg text-sm", COLOR_MAP[color])}>{icon}</span>
        )}
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
      </div>
      <p className={clsx("text-xl font-bold tabular-nums", COLOR_MAP[color].split(" ")[0])}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}
