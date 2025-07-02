// frontend/src/pages/EmpresaFormPage.jsx

import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import PageMeta from "../components/common/PageMeta";
import PageBreadcrumb from "../components/common/PageBreadCrumb";
import ComponentCard from "../components/common/ComponentCard";
import Dropzone from "../components/form/form-elements/DropZone";


export default function EmpresaFormPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const [formData, setFormData] = useState({
    nombre_comercial: "",
    nombre: "",
    rfc: "",
    regimen_fiscal: "",
    codigo_postal: "",
    direccion: "",
    telefono: "",
    email: "",
  });

  const [archivoCer, setArchivoCer] = useState(null);
  const [archivoKey, setArchivoKey] = useState(null);

  useEffect(() => {
    if (id) {
      axios
        .get(`${import.meta.env.VITE_API_URL}/empresas/${id}`)
        .then((res) => {
          setFormData(res.data);
        })
        .catch((err) => console.error(err));
    }
  }, [id]);

  const validate = () => {
    const newErrors = {};
    if (!formData.nombre) newErrors.nombre = "El nombre es obligatorio.";
    if (!formData.rfc) newErrors.rfc = "El RFC es obligatorio.";
    if (!formData.regimen_fiscal) newErrors.regimen_fiscal = "El régimen fiscal es obligatorio.";
    if (!formData.codigo_postal) newErrors.codigo_postal = "El código postal es obligatorio.";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    try {
      const data = new FormData();
      Object.entries(formData).forEach(([key, value]) => {
        data.append(key, value);
      });
      if (archivoCer) data.append("archivo_cer", archivoCer);
      if (archivoKey) data.append("archivo_key", archivoKey);

      if (id) {
        await axios.put(`${import.meta.env.VITE_API_URL}/empresas/${id}`, data);
      } else {
        await axios.post(`${import.meta.env.VITE_API_URL}/empresas/`, data);
      }
      navigate("/empresas");
    } catch (error) {
      console.error("Error al guardar empresa:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageMeta
        title={id ? "Editar Empresa | CRM" : "Nueva Empresa | CRM"}
        description="Formulario de empresa para el CRM."
      />
      <PageBreadcrumb pageTitle={id ? "Editar Empresa" : "Nueva Empresa"} />
      <ComponentCard title={id ? "Editar Empresa" : "Nueva Empresa"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { name: "nombre_comercial", label: "Nombre Comercial" },
            { name: "nombre", label: "Nombre" },
            { name: "rfc", label: "RFC" },
            { name: "regimen_fiscal", label: "Régimen Fiscal" },
            { name: "codigo_postal", label: "Código Postal" },
            { name: "direccion", label: "Dirección" },
            { name: "telefono", label: "Teléfono" },
            { name: "email", label: "Email" },
          ].map((field) => (
            <div key={field.name}>
              <label className="block text-sm font-medium mb-1">{field.label}</label>
              <input
                type="text"
                value={formData[field.name] || ""}
                onChange={(e) =>
                  setFormData({ ...formData, [field.name]: e.target.value })
                }
                className="w-full border border-gray-300 px-3 py-2 rounded text-sm"
              />
              {errors[field.name] && (
                <p className="text-red-500 text-xs mt-1">{errors[field.name]}</p>
              )}
            </div>
          ))}

          <div>
            <label className="block text-sm font-medium mb-1">Archivo CER</label>
            <Dropzone onFileSelect={(file) => setArchivoCer(file)} />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Archivo KEY</label>
            <Dropzone onFileSelect={(file) => setArchivoKey(file)} />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => navigate("/empresas")}
              className="px-4 py-2 border rounded-md text-gray-700 hover:bg-gray-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            >
              {loading ? "Guardando..." : id ? "Actualizar" : "Guardar"}
            </button>
          </div>
        </form>
      </ComponentCard>
    </>
  );
}
