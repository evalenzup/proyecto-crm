import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import PageMeta from "../components/common/PageMeta";
import PageBreadcrumb from "../components/common/PageBreadCrumb";
import ComponentCard from "../components/common/ComponentCard";
import Label from "../components/form/Label";
import Select from "../components/form/Select";
import Alert from "../components/ui/alert/Alert";

export default function EmpresaFormPage() {
  const navigate = useNavigate();
  const { id } = useParams();

  const [formData, setFormData] = useState({});
  const [errors, setErrors] = useState({});
  const [errorAlert, setErrorAlert] = useState("");
  const [schema, setSchema] = useState({ properties: {}, required: [] });
  const [regimenesFiscales, setRegimenesFiscales] = useState([]);

  // Cargar esquema dinámico
  useEffect(() => {
    axios
      .get(`${import.meta.env.VITE_API_URL}/empresas/schema`)
      .then(({ data }) => setSchema(data))
      .catch((err) => console.error("Error cargando esquema:", err));
  }, []);

  // Cargar catálogo de regímenes fiscales
  useEffect(() => {
    axios
      .get(`${import.meta.env.VITE_API_URL}/catalogos/regimen-fiscal`)
      .then(({ data }) => setRegimenesFiscales(Array.isArray(data) ? data : []))
      .catch((err) => console.error("Error al cargar catálogo SAT:", err));
  }, []);

  // Cargar datos si es edición
  useEffect(() => {
    if (!id) return;
    axios
      .get(`${import.meta.env.VITE_API_URL}/empresas/${id}`)
      .then(({ data }) => setFormData(data))
      .catch((err) => console.error(err));
  }, [id]);

  // Validación genérica
  const validate = () => {
    const newErr = {};
    schema.required.forEach((f) => {
      const v = formData[f];
      if (v == null || String(v).trim() === "") {
        newErr[f] = (schema.properties[f].title || f) + " es obligatorio.";
      }
    });
    setErrors(newErr);
    if (Object.keys(newErr).length) {
      setErrorAlert("Por favor completa los campos obligatorios.");
      return false;
    }
    setErrorAlert("");
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    const fd = new FormData();
    Object.entries(formData).forEach(([k, v]) => {
      if ((k === "archivo_cer" || k === "archivo_key") && v instanceof File) {
        fd.append(k, v);
      } else if (k !== "archivo_cer" && k !== "archivo_key" && v != null && v !== "") {
        fd.append(k, v);
      }
    });

    try {
      if (id) {
        await axios.put(
          `${import.meta.env.VITE_API_URL}/empresas/${id}`,
          fd,
          {
            headers: { "Content-Type": "multipart/form-data" },
            transformRequest: [(d) => d],
          }
        );
      } else {
        await axios.post(
          `${import.meta.env.VITE_API_URL}/empresas/`,
          fd,
          {
            headers: { "Content-Type": "multipart/form-data" },
            transformRequest: [(d) => d],
          }
        );
      }
      navigate("/empresas");
    } catch (err) {
      const det = err.response?.data?.detail;
      let msg = "Error al guardar. Por favor intenta nuevamente.";
      if (Array.isArray(det)) {
        const apiErr = {};
        det.forEach((x) => {
          if (x.loc[1]) apiErr[x.loc[1]] = x.msg;
        });
        setErrors(apiErr);
        msg = det.map((x) => x.msg).join(", ");
      } else if (typeof det === "string") {
        msg = det;
      }
      setErrorAlert(msg);
    }
  };

  // Preparar opciones y opción seleccionada para el Select
  const regimenOptions = regimenesFiscales.map((rf) => ({
    value: rf.clave,
    label: `${rf.clave} – ${rf.descripcion}`,
  }));
  const selectedRegimen =
    regimenOptions.find((opt) => opt.value === formData.regimen_fiscal) || null;

  return (
    <>
      <PageMeta
        title={id ? "Editar Empresa" : "Nueva Empresa"}
        description="Formulario dinámico para CRM"
      />
      <PageBreadcrumb
        pageTitle={id ? "Editar Empresa" : "Nueva Empresa"}
      />
      <ComponentCard
        title={id ? "Editar Empresa" : "Nueva Empresa"}
      >
        {errorAlert && (
          <Alert
            variant="error"
            title="Error"
            message={errorAlert}
          />
        )}
        <form
          onSubmit={handleSubmit}
          className="space-y-4"
        >
          {Object.entries(schema.properties).map(
            ([key, prop]) => {
              // Dropdown Régimen Fiscal
              if (key === "regimen_fiscal") {
                return (
                  <div key={key}>
                    <Label htmlFor={key}>{prop.title}</Label>
                    <Select
                      id={key}
                      name={key}
                      options={regimenOptions}
                      value={selectedRegimen}
                      defaultValue={selectedRegimen}
                      onChange={(opt) =>
                        setFormData({
                          ...formData,
                          regimen_fiscal: opt.value,
                        })
                      }
                    />
                    {errors[key] && (
                      <p className="text-red-500 text-xs mt-1">
                        {errors[key]}
                      </p>
                    )}
                  </div>
                );
              }

              // Carga de archivos (.cer / .key)
              if (prop.format === "binary") {
                const accept =
                  key === "archivo_cer" ? ".cer" : ".key";
                return (
                  <div key={key}>
                    <Label htmlFor={key}>{prop.title}</Label>
                    {formData[key] &&
                      !(formData[key] instanceof File) && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                          Archivo actual: {formData[key].split("/").pop()}
                        </p>
                      )}
                    <input
                      id={key}
                      type="file"
                      accept={accept}
                      onChange={(e) => {
                        const f = e.target.files[0];
                        if (
                          f &&
                          f.name
                            .toLowerCase()
                            .endsWith(accept)
                        ) {
                          setFormData({
                            ...formData,
                            [key]: f,
                          });
                          setErrors({
                            ...errors,
                            [key]: null,
                          });
                        } else {
                          setErrors({
                            ...errors,
                            [key]: `Solo archivos ${accept} permitidos.`,
                          });
                          e.target.value = "";
                        }
                      }}
                      className="w-full border border-gray-300 px-3 py-2 rounded text-sm cursor-pointer file:mr-4 file:py-2 file:px-4 file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-gray-700 dark:file:text-gray-200"
                    />
                    {errors[key] && (
                      <p className="text-red-500 text-xs mt-1">
                        {errors[key]}
                      </p>
                    )}
                  </div>
                );
              }

              // Inputs de texto / contraseña
              return (
                <div key={key}>
                  <Label htmlFor={key}>{prop.title}</Label>
                  <input
                    id={key}
                    type={
                      prop.format === "password"
                        ? "password"
                        : "text"
                    }
                    value={formData[key] || ""}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        [key]: e.target.value,
                      })
                    }
                    className="w-full border border-gray-300 px-3 py-2 rounded text-sm focus:outline-none focus:ring focus:border-blue-300 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100"
                  />
                  {errors[key] && (
                    <p className="text-red-500 text-xs mt-1">
                      {errors[key]}
                    </p>
                  )}
                </div>
              );
            }
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => navigate("/empresas")}
              className="px-4 py-2 border rounded text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-700"
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
