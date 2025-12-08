import axiosInstance from "./axiosConfig";

export interface SourcingPlatform {
    id?: string;
    platform_name: string;
    api_key: string;
    client_secret?: string; // For services like LinkedIn that use OAuth
    webhook_url?: string; // The URL the backend generates for the platform to call
}

export const addSourcingPlatform = async (platformData: SourcingPlatform) => {
    try {
        const response = await axiosInstance.post("/sourcing/platforms", platformData);
        return { success: true, data: response.data };
    } catch (err: any) {
        return { success: false, error: err.response?.data?.message || err.message };
    }
};

export const getSourcingPlatforms = async () => {
    try {
        const response = await axiosInstance.get("/sourcing/platforms");
        return { success: true, data: response.data };
    } catch (err: any) {
        return { success: false, error: err.response?.data?.message || err.message };
    }
};

export const deleteSourcingPlatform = async (platformId: string) => {
    try {
        const response = await axiosInstance.delete(`/sourcing/platforms/${platformId}`);
        return { success: true, data: response.data };
    } catch (err: any) {
        return { success: false, error: err.response?.data?.message || err.message };
    }
};
