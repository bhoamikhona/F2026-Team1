import { useParams } from "react-router-dom";
import BackLink from "../components/BackLink.jsx";

function Results() {
  const { id } = useParams();

  return (
    <main className="main">
      <BackLink to="/history">Back to History</BackLink>
      <p className="body-md">Screening {id}</p>
    </main>
  );
}

export default Results;
