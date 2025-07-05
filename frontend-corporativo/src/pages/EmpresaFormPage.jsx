import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import PageMeta from "../components/common/PageMeta";
import PageBreadcrumb from "../components/common/PageBreadCrumb";
import ComponentCard from "../components/common/ComponentCard";

export default function EmpresaFormPage() {
  const navigate = useNavigate();
  const { id } = useParams();

  const [formData, setFormData] = useState({
    nombre: "",
    nombre_comercial: "",
    ruc: "",
    direccion: "",
    telefono: "",
    email: "",
    rfc: "",
    regimen_fiscal: "",
    codigo_postal: "",
    contrasena: "",
    archivo_cer: null,
    archivo_key: null,
  });

  useEffect(() => {
    if (id) {
      axios
        .get(`${import.meta.env.VITE_API_URL}/empresas/${id}`)
        .then((res) => setFormData(res.data))
        .catch((err) => console.error(err));
    }
  }, [id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = new FormData();
      Object.entries(formData).forEach(([key, value]) => {
        data.append(key, value);
      });

      if (id) {
        await axios.put(`${import.meta.env.VITE_API_URL}/empresas/${id}`, data, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } else {
        await axios.post(`${import.meta.env.VITE_API_URL}/empresas/`, data, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      navigate("/empresas");
    } catch (error) {
      console.error("Error al guardar empresa:", error);
    }
  };

  return (
    <>
      <PageMeta
        title={id ? "Editar Empresa" : "Nueva Empresa"}
        description="Formulario de empresa para CRM de facturación"
      />
      <PageBreadcrumb pageTitle={id ? "Editar Empresa" : "Nueva Empresa"} />
      <ComponentCard title={id ? "Editar Empresa" : "Nueva Empresa"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { name: "nombre", label: "Nombre" },
            { name: "nombre_comercial", label: "Nombre Comercial" },
            { name: "ruc", label: "RUC" },
            { name: "direccion", label: "Dirección" },
            { name: "telefono", label: "Teléfono" },
            { name: "email", label: "Email" },
            { name: "rfc", label: "RFC" },
            { name: "regimen_fiscal", label: "Régimen Fiscal" },
            { name: "codigo_postal", label: "Código Postal" },
            { name: "contrasena", label: "Contraseña de Certificados" },
          ].map((field) => (
            <div key={field.name}>
              <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-400">
                {field.label}
              </label>
              <input
                type="text"
                value={formData[field.name] || ""}
                onChange={(e) =>
                  setFormData({ ...formData, [field.name]: e.target.value })
                }
                className="w-full border border-gray-300 px-3 py-2 rounded text-sm 
                  focus:outline-none focus:ring focus:border-blue-300
                  dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100"
              />
            </div>
          ))}

          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-400">
              Archivo CER
            </label>
            <input
              type="file"
              accept=".cer"
              onChange={(e) => {
                const file = e.target.files[0];
                if (file && file.name.endsWith(".cer")) {
                  setFormData((prev) => ({ ...prev, archivo_cer: file }));
                } else {
                  alert("Por favor selecciona un archivo .cer válido.");
                  e.target.value = "";
                }
              }}
              className="w-full border border-gray-300 px-3 py-2 rounded text-sm cursor-pointer
                file:mr-4 file:py-2 file:px-4 file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100
                dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-400">
              Archivo KEY
            </label>
            <input
              type="file"
              accept=".key"
              onChange={(e) => {
                const file = e.target.files[0];
                if (file && file.name.endsWith(".key")) {
                  setFormData((prev) => ({ ...prev, archivo_key: file }));
                } else {
                  alert("Por favor selecciona un archivo .key válido.");
                  e.target.value = "";
                }
              }}
              className="w-full border border-gray-300 px-3 py-2 rounded text-sm cursor-pointer
                file:mr-4 file:py-2 file:px-4 file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100
                dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100"
            />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => navigate("/empresas")}
              className="px-4 py-2 border rounded-md text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              {id ? "Actualizar" : "Guardar"}
            </button>
          </div>
        </form>
      </ComponentCard>
    </>
  );
}
