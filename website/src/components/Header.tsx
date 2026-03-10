import ConvexClientProvider from "./ConvexClientProvider";
import AuthSection from "./AuthSection";

export default function Header() {
    return (
        <ConvexClientProvider>
            <AuthSection />
        </ConvexClientProvider>
    );
}
