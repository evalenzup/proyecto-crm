import { useEffect, useState } from "react";
import axios from "axios";
import { Pencil, Trash2, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import PageMeta from "../components/common/PageMeta";
import PageBreadcrumb from "../components/common/PageBreadCrumb";
import ComponentCard from "../components/common/ComponentCard";

export default function EmpresasPage() {
  const [empresas, setEmpresas] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const navigate = useNavigate();

  const obtenerEmpresas = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/empresas/`);
      setEmpresas(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error("Error al obtener empresas:", error);
      setEmpresas([]);
    }
  };

  useEffect(() => {
    obtenerEmpresas();
  }, []);

  const handleDelete = async (id) => {
    if (!confirm("¿Seguro que deseas eliminar esta empresa?")) return;
    try {
      await axios.delete(`${import.meta.env.VITE_API_URL}/empresas/${id}`);
      obtenerEmpresas();
    } catch (error) {
      console.error("Error al eliminar empresa:", error);
    }
  };

  const empresasFiltradas = empresas.filter((empresa) =>
    empresa.nombre?.toLowerCase().includes(busqueda.toLowerCase())
  );

  return (
    <>
      <PageMeta
        title="Empresas | CRM Facturación"
        description="Gestión de empresas para el CRM de facturación."
      />
      <PageBreadcrumb pageTitle="Empresas" />

      <ComponentCard title="Listado de Empresas">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4 gap-2">
          <input
            type="text"
            placeholder="Buscar empresa..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full md:w-1/3 rounded-lg border border-stroke bg-transparent py-2 px-4 text-black dark:text-white dark:border-strokedark dark:bg-boxdark focus:border-primary focus:outline-none"
          />
          <button
            onClick={() => navigate("/empresas/nueva")}
            class="inline-flex items-center justify-center gap-2 rounded-lg transition  px-4 py-3 text-sm bg-brand-500 text-white shadow-theme-xs hover:bg-brand-600 disabled:bg-brand-300 ">
            Nueva Empresa
            <Plus size={18} />
          </button>
          
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-boxdark text-sm rounded-lg">
            <thead className="bg-gray-100 dark:bg-gray-800">
              <tr>
                {["Nombre", "RFC", "Régimen Fiscal", "Código Postal", "Teléfono", "Email", "Acciones"].map((header) => (
                  <th key={header} className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {empresasFiltradas.length > 0 ? (
                empresasFiltradas.map((empresa) => (
                  <tr key={empresa.id} className="border-t border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-4 py-2">{empresa.nombre}</td>
                    <td className="px-4 py-2">{empresa.rfc}</td>
                    <td className="px-4 py-2">{empresa.regimen_fiscal}</td>
                    <td className="px-4 py-2">{empresa.codigo_postal}</td>
                    <td className="px-4 py-2">{empresa.telefono}</td>
                    <td className="px-4 py-2">{empresa.email}</td>
                    <td className="px-4 py-2 flex gap-2">
                      <button
                        onClick={() => navigate(`/empresas/editar/${empresa.id}`)}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <Pencil size={18} />
                      </button>
                      <button
                        onClick={() => handleDelete(empresa.id)}
                        className="text-red-600 hover:text-red-800"
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-4 py-4 text-center text-gray-500 dark:text-gray-400">
                    No se encontraron empresas.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </ComponentCard>
    </>
  );
}
