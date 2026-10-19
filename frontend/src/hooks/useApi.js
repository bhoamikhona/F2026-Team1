import { useEffect, useState } from "react";
import { apiGet } from "../services/api.js";

export function useApi(path) {
  const [result, setResult] = useState({ path: null, data: null, error: null });

  useEffect(() => {
    let ignore = false;

    apiGet(path)
      .then((data) => {
        if (!ignore) setResult({ path, data, error: null });
      })
      .catch((error) => {
        if (!ignore) setResult({ path, data: null, error });
      });

    return () => {
      ignore = true;
    };
  }, [path]);

  const isLoading = result.path !== path;

  return {
    data: isLoading ? null : result.data,
    error: isLoading ? null : result.error,
    isLoading,
  };
}
