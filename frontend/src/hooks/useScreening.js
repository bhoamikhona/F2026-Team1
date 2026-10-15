import { useEffect, useState } from "react";
import { apiGet } from "../services/api.js";

export function useScreening(id) {
  const [result, setResult] = useState({
    id: null,
    screening: null,
    error: null,
  });

  useEffect(() => {
    let ignore = false;

    apiGet(`/screenings/${id}`)
      .then((screening) => {
        if (!ignore) setResult({ id, screening, error: null });
      })
      .catch((error) => {
        if (!ignore) setResult({ id, screening: null, error });
      });

    return () => {
      ignore = true;
    };
  }, [id]);

  const isLoading = result.id !== id;

  return {
    screening: isLoading ? null : result.screening,
    error: isLoading ? null : result.error,
    isLoading,
  };
}
