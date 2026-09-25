return {
  name = "placeholder-hint",
  validate = function(source, target)
    if source:find("$COUNTRY", 1, true) and not target:find("$COUNTRY", 1, true) then
      return { valid = false, error = "Missing $COUNTRY placeholder" }
    end
    return { valid = true }
  end
}
