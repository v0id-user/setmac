return {
  {
    "metalelf0/black-metal-theme-neovim",
    lazy = false, -- Load right away for colors
    priority = 1000, -- Load before other plugins
    config = function()
      vim.o.background = "dark"
      vim.cmd.colorscheme("marduk") -- This loads the Marduk variant
    end,
  },
}
