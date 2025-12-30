/**
 * Favorites/Bookmarks Store
 * Manages user's saved/marked locations for future reference
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface FavoriteLocation {
  regionId: string;
  regionName: string;
  regionType: 'lga' | 'suburb';
  timestamp: string; // When it was marked
  notes?: string; // Optional user notes for next semester
}

interface FavoritesState {
  favorites: FavoriteLocation[];
  
  // Actions
  addFavorite: (location: FavoriteLocation) => void;
  removeFavorite: (regionId: string) => void;
  updateFavoriteNotes: (regionId: string, notes: string) => void;
  isFavorite: (regionId: string) => boolean;
  getFavorite: (regionId: string) => FavoriteLocation | undefined;
  clearAllFavorites: () => void;
  getFavoriteCount: () => number;
}

export const useFavoritesStore = create<FavoritesState>()(
  persist(
    (set, get) => ({
      favorites: [],

      addFavorite: (location) =>
        set((state) => {
          // Prevent duplicates
          const exists = state.favorites.some((fav) => fav.regionId === location.regionId);
          if (exists) {
            return state;
          }

          return {
            favorites: [...state.favorites, location],
          };
        }),

      removeFavorite: (regionId) =>
        set((state) => ({
          favorites: state.favorites.filter((fav) => fav.regionId !== regionId),
        })),

      updateFavoriteNotes: (regionId, notes) =>
        set((state) => ({
          favorites: state.favorites.map((fav) =>
            fav.regionId === regionId ? { ...fav, notes } : fav
          ),
        })),

      isFavorite: (regionId) => {
        const state = get();
        return state.favorites.some((fav) => fav.regionId === regionId);
      },

      getFavorite: (regionId) => {
        const state = get();
        return state.favorites.find((fav) => fav.regionId === regionId);
      },

      clearAllFavorites: () => set({ favorites: [] }),

      getFavoriteCount: () => {
        const state = get();
        return state.favorites.length;
      },
    }),
    {
      name: 'clisapp-favorites',
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);