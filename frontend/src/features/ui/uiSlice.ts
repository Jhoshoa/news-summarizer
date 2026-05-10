import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

type UiState = {
  activeCategory: string;
  activeDepartment: string;
  selectedDate: string | null;
};

const initialState: UiState = {
  activeCategory: "general",
  activeDepartment: "la_paz",
  selectedDate: null,
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    setActiveCategory: (state, action: PayloadAction<string>) => {
      state.activeCategory = action.payload;
    },
    setActiveDepartment: (state, action: PayloadAction<string>) => {
      state.activeDepartment = action.payload;
    },
    setSelectedDate: (state, action: PayloadAction<string | null>) => {
      state.selectedDate = action.payload;
    },
  },
});

export const { setActiveCategory, setActiveDepartment, setSelectedDate } = uiSlice.actions;
export default uiSlice.reducer;
