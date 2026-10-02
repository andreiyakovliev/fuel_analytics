import { createContext, useState} from "react";

const AuthConntext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(() => localStorage.getItem('token'))

    const login = (newToken) => {
        localStorage.setItem('token', newToken)
        setToken(newToken)
    }

    const logout = () => {
        localStorage.removeItem('token')
        setToken(null)
    }

    return(
        <AuthConntext.Provider
        value={{
            token,
            login,
            logout,
            isAuthicated: !!token,
        }}
        >
            { children }
        </AuthConntext.Provider>
    )
}