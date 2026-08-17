import { useRef, useState } from "react";
import { Upload, X, CheckCircle, AlertCircle, FileUp } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import type { Account, UploadResult } from "../types";
import { api } from "../api/client";

type State = "idle" | "uploading" | "done" | "error";

interface Props {
  account: Account;
  onClose: () => void;
}

const ACCEPT: Record<string, string> = {
  BBVA: ".xlsx,.csv",
  "Eurocaja Rural": ".csv",
};

const FORMAT_LABEL: Record<string, string> = {
  BBVA: "Excel .xlsx o CSV .csv",
  "Eurocaja Rural": "CSV .csv",
};

export default function UploadModal({ account, onClose }: Props) {
  const [state, setState] = useState<State>("idle");
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string>("");
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const accept = ACCEPT[account.proveedor] ?? ".csv,.xlsx";
  const formatLabel = FORMAT_LABEL[account.proveedor] ?? "CSV o Excel";

  async function handleFile(file: File) {
    setState("uploading");
    setError("");
    try {
      const res = await api.accounts.upload(account.id, file);
      setResult(res);
      setState("done");
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
      setState("error");
    }
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="font-semibold text-gray-900">Importar extracto</h2>
            <p className="text-xs text-gray-500 mt-0.5">{account.alias}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-400"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          {state === "idle" || state === "error" ? (
            <>
              {/* Drop zone */}
              <div
                className={clsx(
                  "border-2 border-dashed rounded-xl p-8 flex flex-col items-center gap-3 cursor-pointer transition-colors",
                  dragging
                    ? "border-blue-400 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                )}
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
              >
                <div className="p-3 rounded-full bg-gray-100">
                  <FileUp size={24} className="text-gray-400" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-700">
                    Arrastra el archivo aquí
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    o haz clic para seleccionar
                  </p>
                </div>
                <span className="text-xs px-3 py-1 rounded-full bg-gray-100 text-gray-500 font-mono">
                  {formatLabel}
                </span>
              </div>
              <input
                ref={inputRef}
                type="file"
                accept={accept}
                className="hidden"
                onChange={onFileChange}
              />

              {state === "error" && (
                <div className="mt-4 flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-100">
                  <AlertCircle size={16} className="text-red-500 mt-0.5 shrink-0" />
                  <p className="text-xs text-red-700">{error}</p>
                </div>
              )}
            </>
          ) : state === "uploading" ? (
            <div className="py-8 flex flex-col items-center gap-3 text-gray-500">
              <Upload size={32} className="animate-bounce text-blue-400" />
              <p className="text-sm font-medium">Importando...</p>
            </div>
          ) : (
            /* done */
            <div className="py-4 flex flex-col items-center gap-4">
              <CheckCircle size={40} className="text-green-500" />
              <div className="text-center">
                <p className="font-semibold text-gray-900">
                  {result!.imported} transacciones nuevas
                </p>
                {result!.skipped_duplicates > 0 && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    {result!.skipped_duplicates} duplicadas omitidas
                  </p>
                )}
                {result!.balance != null && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    Saldo: {result!.balance.toLocaleString("es-ES", { style: "currency", currency: "EUR" })}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-2">
          {state === "done" ? (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors"
            >
              Cerrar
            </button>
          ) : state === "error" ? (
            <>
              <button
                onClick={() => { setState("idle"); setError(""); }}
                className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Reintentar
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
            </>
          ) : state === "idle" ? (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
