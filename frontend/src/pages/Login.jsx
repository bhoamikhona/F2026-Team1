import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { LogIn, Mail, Lock, UserRound } from "lucide-react";
import Alert from "../components/Alert.jsx";
import AuthLayout from "../components/auth/AuthLayout.jsx";
import Button from "../components/Button.jsx";
import Input from "../components/Input.jsx";
import useAuth from "../hooks/useAuth.js";

const DEMO_EMAIL = import.meta.env.VITE_DEV_EMAIL;
const DEMO_PASSWORD = import.meta.env.VITE_DEV_PASSWORD;

function validate({ email, password }) {
  const errors = {};

  if (!email.trim()) errors.email = "Enter your email address.";
  if (!password) errors.password = "Enter your password.";

  return errors;
}

function Login() {
  const { user, isLoading, login } = useAuth();
  const location = useLocation();
  const from = location.state?.from?.pathname ?? "/";

  const [values, setValues] = useState({ email: "", password: "" });
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const errors = submitted ? validate(values) : {};

  function handleChange(e) {
    const { name, value } = e.target;
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  async function signIn(email, password) {
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setSubmitError(err.message);
      setIsSubmitting(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    setSubmitted(true);

    if (Object.keys(validate(values)).length > 0) return;

    signIn(values.email.trim(), values.password);
  }

  function handleDemo() {
    setSubmitted(false);
    signIn(DEMO_EMAIL, DEMO_PASSWORD);
  }

  if (isLoading) return null;
  if (user) return <Navigate to={from} replace />;

  return (
    <AuthLayout
      title="Sign in"
      subtitle="Use your clinic account to start screening."
    >
      {submitError && <Alert title="Could not sign in">{submitError}</Alert>}

      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <Input
          label="Email"
          name="email"
          type="email"
          icon={Mail}
          placeholder="name@clinic.com"
          autoComplete="email"
          value={values.email}
          onChange={handleChange}
          error={errors.email}
        />
        <Input
          label="Password"
          name="password"
          type="password"
          icon={Lock}
          placeholder="Enter your password"
          autoComplete="current-password"
          value={values.password}
          onChange={handleChange}
          error={errors.password}
        />
        <Button type="submit" icon={LogIn} fullWidth disabled={isSubmitting}>
          {isSubmitting ? "Signing in" : "Sign in"}
        </Button>
      </form>

      <div className="auth-demo">
        <p className="auth-demo__divider caption-md">or</p>

        <Button
          variant="secondary"
          icon={UserRound}
          fullWidth
          disabled={isSubmitting}
          onClick={handleDemo}
        >
          Use demo account
        </Button>

        <p className="auth-demo__note caption-rg">
          Try DUAL with sample patients and mock results.
        </p>
      </div>
    </AuthLayout>
  );
}

export default Login;
