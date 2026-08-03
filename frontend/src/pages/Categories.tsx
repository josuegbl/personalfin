import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export default function Categories() {
  const { data: categories, isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: api.categories.list,
  });

  return (
    <div className="p-6 space-y-4 max-w-3xl mx-auto">
      <h2 className="text-xl font-bold text-gray-900">Categorías</h2>

      {isLoading ? (
        <p className="text-gray-400 text-sm">Cargando…</p>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3 text-left">Categoría</th>
                <th className="px-4 py-3 text-left">Color</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {categories?.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span>{c.icono}</span>
                      <span className="font-medium text-gray-800">{c.nombre}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-5 h-5 rounded-full border border-gray-200"
                        style={{ background: c.color ?? "#e5e7eb" }}
                      />
                      <span className="text-xs text-gray-400 font-mono">{c.color ?? "—"}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
